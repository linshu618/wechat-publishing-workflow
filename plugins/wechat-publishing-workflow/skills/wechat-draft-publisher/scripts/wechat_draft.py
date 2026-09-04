#!/usr/bin/env python3
"""把准备好的 HTML 内容发布到公众号草稿箱。"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import sys
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

CONFIG_ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "wechat-draft-publisher"
CONFIG_PATH = CONFIG_ROOT / "credentials.json"
LEGACY_CONFIG_PATH = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "wechat-html-editor" / "credentials.json"
MAX_ARTICLE_IMAGE_BYTES = 1024 * 1024
MAX_COVER_BYTES = 10 * 1024 * 1024
HTTP_TIMEOUT_SECONDS = 90
DEFAULT_PUBLISH_DEFAULTS = {
    "author": "",
    "contentSourceUrl": "",
    "needOpenComment": True,
}


class ChineseArgumentParser(argparse.ArgumentParser):
    """显示中文标题和帮助操作的命令行参数解析器。"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("add_help", False)
        super().__init__(*args, **kwargs)
        self._positionals.title = "位置参数"
        self._optionals.title = "选项"
        self.add_argument("-h", "--help", action="help", help="显示帮助信息并退出")

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法：", 1)

    def format_help(self) -> str:
        return super().format_help().replace("usage:", "用法：", 1)


class WeChatApiError(RuntimeError):
    def __init__(self, message: str, code: int | None = None, detail: str | None = None):
        super().__init__(message)
        self.code = code
        self.detail = detail


def explain_wechat_error(result: dict[str, Any]) -> str:
    code = _integer_or_none(result.get("errcode"))
    messages = {
        40005: "微信不支持这种图片格式",
        40006: "图片文件过大",
        40009: "图片文件大小不符合微信要求",
        40013: "AppID 无效，请检查是否复制完整",
        40125: "AppSecret 无效；如果刚刚重置，请使用新的 AppSecret",
        40164: "当前公网 IP 不在公众号 IP 白名单中",
        45009: "微信接口调用次数已达到当日上限",
        48001: "该公众号没有草稿接口权限",
    }
    return messages.get(code) or str(result.get("errmsg") or f"微信接口返回错误 {code or '未知'}")


def _integer_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _request_json(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request = Request(url, data=body, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read()
    except HTTPError as error:
        raw = error.read()
        try:
            result = json.loads(raw.decode("utf-8"))
        except Exception:
            raise WeChatApiError(f"微信接口 HTTP {error.code}") from error
        raise WeChatApiError(explain_wechat_error(result), _integer_or_none(result.get("errcode")), result.get("errmsg")) from error
    except URLError as error:
        raise WeChatApiError(f"无法连接微信接口：{error.reason}") from error
    try:
        result = json.loads(raw.decode("utf-8"))
    except Exception as error:
        raise WeChatApiError("微信接口返回了无法解析的数据") from error
    if _integer_or_none(result.get("errcode")) not in (None, 0):
        raise WeChatApiError(explain_wechat_error(result), _integer_or_none(result.get("errcode")), result.get("errmsg"))
    return result


def _dpapi(mode: str, value: str) -> str:
    if os.name != "nt":
        raise RuntimeError("AppSecret 本地加密目前只支持 Windows DPAPI")
    if mode == "protect":
        script = (
            "Add-Type -AssemblyName System.Security;"
            "$value=[Console]::In.ReadToEnd();"
            "$bytes=[Text.Encoding]::UTF8.GetBytes($value);"
            "$protected=[Security.Cryptography.ProtectedData]::Protect($bytes,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser);"
            "[Console]::Out.Write([Convert]::ToBase64String($protected))"
        )
    else:
        script = (
            "Add-Type -AssemblyName System.Security;"
            "$value=[Console]::In.ReadToEnd();"
            "$protected=[Convert]::FromBase64String($value);"
            "$bytes=[Security.Cryptography.ProtectedData]::Unprotect($protected,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser);"
            "[Console]::Out.Write([Text.Encoding]::UTF8.GetString($bytes))"
        )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        input=value,
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Windows 凭据加密失败")
    return completed.stdout


def _migrate_legacy_credentials() -> None:
    if CONFIG_PATH.exists() or not LEGACY_CONFIG_PATH.exists():
        return
    try:
        config = json.loads(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    if not config.get("appid") or not config.get("protectedSecret"):
        return
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, CONFIG_PATH)


def normalize_publish_defaults(value: dict[str, Any] | None = None) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    author = str(source.get("author") or "").strip()
    content_source_url = str(source.get("contentSourceUrl") or "").strip()
    raw_open_comment = source.get("needOpenComment", True)
    if len(author) > 16:
        raise ValueError("默认作者不能超过 16 个字符")
    if len(content_source_url.encode("utf-8")) > 1024:
        raise ValueError("默认阅读原文链接不能超过 1KB")
    if content_source_url:
        parsed = urlparse(content_source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("默认阅读原文链接必须是有效的 HTTP 或 HTTPS 地址")
    if isinstance(raw_open_comment, bool):
        need_open_comment = raw_open_comment
    elif raw_open_comment in {0, 1}:
        need_open_comment = bool(raw_open_comment)
    else:
        raise ValueError("默认评论开关必须是布尔值")
    return {
        "author": author,
        "contentSourceUrl": content_source_url,
        "needOpenComment": need_open_comment,
    }


def _write_config(config: dict[str, Any]) -> Path:
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, CONFIG_PATH)
    return CONFIG_PATH


def load_publish_defaults() -> dict[str, Any]:
    _migrate_legacy_credentials()
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return dict(DEFAULT_PUBLISH_DEFAULTS)
    except Exception as error:
        raise RuntimeError("本地公众号配置文件损坏，请重新保存") from error
    return normalize_publish_defaults(config.get("defaults"))


def save_credentials(appid: str, secret: str, defaults: dict[str, Any] | None = None) -> Path:
    appid = appid.strip()
    secret = secret.strip()
    if not appid or not secret:
        raise ValueError("AppID 和 AppSecret 不能为空")
    if defaults is None:
        try:
            existing = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            existing_defaults = existing.get("defaults") if str(existing.get("appid") or "").strip() == appid else None
        except Exception:
            existing_defaults = None
        defaults = existing_defaults
    config = {
        "version": 2,
        "appid": appid,
        "protectedSecret": _dpapi("protect", secret),
        "defaults": normalize_publish_defaults(defaults),
    }
    return _write_config(config)


def save_publish_defaults(appid: str, defaults: dict[str, Any]) -> Path:
    appid = appid.strip()
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError("尚未保存本机公众号配置") from error
    except Exception as error:
        raise RuntimeError("本地公众号配置文件损坏，请重新保存") from error
    stored_appid = str(config.get("appid") or "").strip()
    if not stored_appid or stored_appid != appid:
        raise RuntimeError("默认发布设置必须保存到当前已配置的公众号账号")
    if not config.get("protectedSecret"):
        raise RuntimeError("本地公众号配置不完整，请重新保存")
    config["version"] = 2
    config["defaults"] = normalize_publish_defaults(defaults)
    return _write_config(config)


def load_credentials() -> tuple[str, str]:
    _migrate_legacy_credentials()
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError("尚未保存本机公众号配置") from error
    except Exception as error:
        raise RuntimeError("本地公众号配置文件损坏，请重新保存") from error
    appid = str(config.get("appid") or "").strip()
    protected = str(config.get("protectedSecret") or "").strip()
    if not appid or not protected:
        raise RuntimeError("本地公众号配置不完整，请重新保存")
    try:
        return appid, _dpapi("unprotect", protected)
    except Exception as error:
        raise RuntimeError("本地 AppSecret 无法解密，请使用当前 Windows 用户重新保存") from error


def credential_status() -> dict[str, Any]:
    _migrate_legacy_credentials()
    if not CONFIG_PATH.exists():
        return {
            "configured": False,
            "appid": "",
            "path": str(CONFIG_PATH),
            "defaults": dict(DEFAULT_PUBLISH_DEFAULTS),
        }
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        appid = str(config.get("appid") or "").strip()
        configured = bool(appid and config.get("protectedSecret"))
        defaults = normalize_publish_defaults(config.get("defaults"))
    except Exception:
        appid, configured, defaults = "", False, dict(DEFAULT_PUBLISH_DEFAULTS)
    return {"configured": configured, "appid": appid, "path": str(CONFIG_PATH), "defaults": defaults}


def resolve_credentials(appid: str = "", secret: str = "") -> tuple[str, str]:
    appid = appid.strip()
    secret = secret.strip()
    if appid and secret:
        return appid, secret
    stored_appid, stored_secret = load_credentials()
    if secret:
        return appid or stored_appid, secret
    if appid and appid != stored_appid:
        raise RuntimeError("输入的 AppID 与本机保存的账号不同，请同时提供对应 AppSecret")
    return stored_appid, stored_secret


def get_access_token(appid: str, secret: str) -> str:
    body = json.dumps(
        {"grant_type": "client_credential", "appid": appid, "secret": secret, "force_refresh": False},
        ensure_ascii=False,
    ).encode("utf-8")
    result = _request_json(
        "https://api.weixin.qq.com/cgi-bin/stable_token",
        method="POST",
        body=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    token = str(result.get("access_token") or "")
    if not token:
        raise WeChatApiError(explain_wechat_error(result), _integer_or_none(result.get("errcode")), result.get("errmsg"))
    return token


def test_draft_access(appid: str = "", secret: str = "") -> dict[str, Any]:
    resolved_appid, resolved_secret = resolve_credentials(appid, secret)
    access_token = get_access_token(resolved_appid, resolved_secret)
    result = _request_json(f"https://api.weixin.qq.com/cgi-bin/draft/count?access_token={quote(access_token)}")
    if not isinstance(result.get("total_count"), int):
        raise WeChatApiError(explain_wechat_error(result), _integer_or_none(result.get("errcode")), result.get("errmsg"))
    return {"ok": True, "appid": resolved_appid, "totalCount": result["total_count"]}


def _multipart_body(bytes_value: bytes, mime_type: str, filename: str) -> tuple[bytes, str]:
    boundary = "----CodexWechat" + uuid.uuid4().hex
    safe_filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{safe_filename}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("ascii")
    tail = f"\r\n--{boundary}--\r\n".encode("ascii")
    return head + bytes_value + tail, boundary


def upload_image(access_token: str, bytes_value: bytes, mime_type: str, filename: str, endpoint: str) -> dict[str, Any]:
    body, boundary = _multipart_body(bytes_value, mime_type, filename)
    separator = "&" if "?" in endpoint else "?"
    return _request_json(
        f"{endpoint}{separator}access_token={quote(access_token)}",
        method="POST",
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def _compress_article_image(bytes_value: bytes, mime_type: str) -> tuple[bytes, str, str]:
    if len(bytes_value) <= MAX_ARTICLE_IMAGE_BYTES:
        return bytes_value, mime_type, "png" if mime_type == "image/png" else "jpg"
    try:
        from PIL import Image
    except ImportError as error:
        raise ValueError(f"正文图片超过 1MB（当前 {len(bytes_value) / 1024 / 1024:.2f}MB），并且没有 Pillow 可用于压缩") from error
    image = Image.open(BytesIO(bytes_value))
    image.thumbnail((2400, 2400))
    if image.mode not in ("RGB", "L"):
        background = Image.new("RGB", image.size, "white")
        if "A" in image.getbands():
            background.paste(image, mask=image.getchannel("A"))
        else:
            background.paste(image.convert("RGB"))
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")
    for quality in (88, 80, 72, 64, 56, 48):
        output = BytesIO()
        image.save(output, format="JPEG", quality=quality, optimize=True)
        compressed = output.getvalue()
        if len(compressed) <= MAX_ARTICLE_IMAGE_BYTES:
            return compressed, "image/jpeg", "jpg"
    raise ValueError(f"正文图片压缩后仍超过 1MB（当前 {len(compressed) / 1024 / 1024:.2f}MB）")


def decode_data_image(source: str) -> tuple[bytes, str, str]:
    match = re.fullmatch(r"data:(image/(?:png|jpeg|jpg));base64,([A-Za-z0-9+/=\r\n]+)", source, flags=re.IGNORECASE)
    if not match:
        raise ValueError("正文图片必须是 JPG/PNG 数据图片；请通过编辑器重新插入")
    mime_type = match.group(1).lower().replace("image/jpg", "image/jpeg")
    try:
        bytes_value = base64.b64decode(re.sub(r"\s", "", match.group(2)), validate=True)
    except ValueError as error:
        raise ValueError("正文图片数据损坏") from error
    return _compress_article_image(bytes_value, mime_type)


def upload_article_images(appid: str, access_token: str, content: str) -> str:
    pattern = re.compile(r"<img\b[^>]*?\bsrc=(['\"])(.*?)\1[^>]*>", flags=re.IGNORECASE | re.DOTALL)
    sources = list(dict.fromkeys(match.group(2) for match in pattern.finditer(content)))
    replacements: dict[str, str] = {}
    for source in sources:
        if re.match(r"^https://mmbiz\.(?:qpic|qlogo)\.cn/", source, flags=re.IGNORECASE):
            continue
        bytes_value, mime_type, extension = decode_data_image(source)
        digest = hashlib.sha256(bytes_value).hexdigest()
        result = upload_image(
            access_token,
            bytes_value,
            mime_type,
            f"article-{digest[:12]}.{extension}",
            "https://api.weixin.qq.com/cgi-bin/media/uploadimg",
        )
        url = str(result.get("url") or "")
        if not url:
            raise WeChatApiError("微信没有返回正文图片地址")
        replacements[source] = url
    for source, url in replacements.items():
        content = content.replace(source, url)
    return content


def _detect_image_type(bytes_value: bytes, filename: str = "cover") -> tuple[str, str]:
    if bytes_value.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if bytes_value.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    guessed = mimetypes.guess_type(filename)[0]
    if guessed in {"image/png", "image/jpeg"}:
        return guessed, "png" if guessed == "image/png" else "jpg"
    raise ValueError("封面必须是 PNG 或 JPEG")


def decode_cover_data(source: str) -> tuple[bytes, str, str]:
    bytes_value, mime_type, extension = decode_data_image(source)
    if len(bytes_value) > MAX_COVER_BYTES:
        raise ValueError("封面超过 10MB")
    return bytes_value, mime_type, extension


def read_cover_file(path_value: str | Path) -> tuple[bytes, str, str]:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"找不到封面：{path}")
    bytes_value = path.read_bytes()
    if len(bytes_value) > MAX_COVER_BYTES:
        raise ValueError("封面超过 10MB")
    mime_type, extension = _detect_image_type(bytes_value, path.name)
    return bytes_value, mime_type, extension


def find_cover(article_directory: Path, explicit: str | Path | None = None) -> Path | None:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        return candidate if candidate.is_file() else None
    versioned: list[tuple[int, float, Path]] = []
    for candidate in article_directory.glob("公众号封面-v*.*"):
        if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        match = re.search(r"-v(\d+)$", candidate.stem)
        versioned.append((int(match.group(1)) if match else 0, candidate.stat().st_mtime, candidate))
    if versioned:
        return max(versioned, key=lambda item: (item[0], item[1]))[2]
    for name in ("公众号封面.png", "公众号封面.jpg", "公众号封面.jpeg"):
        candidate = article_directory / name
        if candidate.is_file():
            return candidate
    return None


def publish_draft(
    *,
    title: str,
    content: str,
    cover_bytes: bytes,
    cover_mime: str,
    cover_extension: str,
    author: str = "",
    digest: str = "",
    content_source_url: str = "",
    need_open_comment: int | bool = 1,
    appid: str = "",
    secret: str = "",
) -> dict[str, Any]:
    title, digest, content = title.strip(), digest.strip(), content.strip()
    publish_defaults = normalize_publish_defaults({
        "author": author,
        "contentSourceUrl": content_source_url,
        "needOpenComment": need_open_comment,
    })
    author = publish_defaults["author"]
    content_source_url = publish_defaults["contentSourceUrl"]
    need_open_comment = int(publish_defaults["needOpenComment"])
    if not title or not content:
        raise ValueError("标题和正文不能为空")
    if len(title) > 64:
        raise ValueError("标题不能超过 64 个字符")
    if len(author) > 16:
        raise ValueError("作者不能超过 16 个字符")
    if len(digest) > 120:
        raise ValueError("摘要不能超过 120 个字符")
    resolved_appid, resolved_secret = resolve_credentials(appid, secret)
    access_token = get_access_token(resolved_appid, resolved_secret)
    uploaded_content = upload_article_images(resolved_appid, access_token, content)
    cover_hash = hashlib.sha256(cover_bytes).hexdigest()
    cover_result = upload_image(
        access_token,
        cover_bytes,
        cover_mime,
        f"cover-{cover_hash[:12]}.{cover_extension}",
        "https://api.weixin.qq.com/cgi-bin/material/add_material?type=image",
    )
    thumb_media_id = str(cover_result.get("media_id") or "")
    if not thumb_media_id:
        raise WeChatApiError("微信没有返回封面素材 ID")
    payload = {
        "articles": [{
            "title": title,
            "author": author,
            "content": uploaded_content,
            "content_source_url": content_source_url,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": need_open_comment,
            "only_fans_can_comment": 0,
        }]
    }
    if digest:
        payload["articles"][0]["digest"] = digest
    result = _request_json(
        f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={quote(access_token)}",
        method="POST",
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    media_id = str(result.get("media_id") or "")
    if not media_id:
        raise WeChatApiError(explain_wechat_error(result), _integer_or_none(result.get("errcode")), result.get("errmsg"))
    return {"ok": True, "appid": resolved_appid, "mediaId": media_id, "thumbMediaId": thumb_media_id}


def extract_article_content(document: str) -> str:
    starts = [
        re.search(r"<(article|main)\b[^>]*\bid\s*=\s*(['\"])article\2[^>]*>", document, flags=re.IGNORECASE),
        re.search(r"<(article)\b[^>]*>", document, flags=re.IGNORECASE),
        re.search(r"<(main)\b[^>]*>", document, flags=re.IGNORECASE),
    ]
    start = next((match for match in starts if match), None)
    if not start:
        raise ValueError("HTML 中找不到 #article、<article> 或 <main> 正文区域")
    tag = start.group(1)
    token_pattern = re.compile(rf"</?{tag}\b[^>]*>", flags=re.IGNORECASE)
    depth = 1
    for token in token_pattern.finditer(document, start.end()):
        if token.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return document[start.end():token.start()].strip()
        elif not token.group(0).rstrip().endswith("/>"):
            depth += 1
    raise ValueError("正文区域的 HTML 标签没有闭合")


def _title_from_document(document: str) -> str:
    match = re.search(r"<title\b[^>]*>(.*?)</title>", document, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else ""


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = ChineseArgumentParser(description="将 HTML 发布到公众号草稿箱。")
    subparsers = parser.add_subparsers(dest="command", required=True, title="命令", metavar="{status,configure,test,publish}")
    subparsers.add_parser("status", help="显示本地凭据状态，但不暴露 AppSecret")
    configure = subparsers.add_parser("configure", help="测试并为当前 Windows 用户加密保存 AppID 和 AppSecret")
    configure.add_argument("--appid", metavar="APPID", required=True, help="公众号 AppID")
    configure.add_argument("--secret-stdin", action="store_true", help="从标准输入读取 AppSecret")
    configure.add_argument("--author", metavar="默认作者", default=None, help="保存默认作者")
    configure.add_argument("--source-url", metavar="默认阅读原文链接", default=None, help="保存默认阅读原文链接")
    configure_comment = configure.add_mutually_exclusive_group()
    configure_comment.add_argument("--open-comment", dest="need_open_comment", action="store_const", const=True, default=None, help="默认开启评论")
    configure_comment.add_argument("--close-comment", dest="need_open_comment", action="store_const", const=False, help="默认关闭评论")
    test = subparsers.add_parser("test", help="测试已保存凭据和 draft/count 接口权限")
    test.add_argument("--appid", metavar="APPID", default="", help="临时指定公众号 AppID")
    publish = subparsers.add_parser("publish", help="创建公众号草稿")
    source = publish.add_mutually_exclusive_group(required=True)
    source.add_argument("--html-file", metavar="HTML文件", type=Path, help="包含完整文章的 HTML 文件")
    source.add_argument("--content-file", metavar="正文文件", type=Path, help="只包含正文片段的 HTML 文件")
    publish.add_argument("--cover", metavar="封面文件", type=Path, help="PNG 或 JPEG 封面文件")
    publish.add_argument("--title", metavar="标题", default="", help="文章标题")
    publish.add_argument("--author", metavar="作者", default=None, help="作者名称；省略时使用账号默认作者")
    publish.add_argument("--digest", metavar="摘要", default="", help="文章摘要")
    publish.add_argument("--source-url", metavar="阅读原文链接", default=None, help="阅读原文链接；省略时使用账号默认链接")
    publish_comment = publish.add_mutually_exclusive_group()
    publish_comment.add_argument("--open-comment", dest="need_open_comment", action="store_const", const=True, default=None, help="开启评论")
    publish_comment.add_argument("--close-comment", dest="need_open_comment", action="store_const", const=False, help="关闭评论")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "status":
            _print_json({"ok": True, **credential_status()})
            return 0
        if args.command == "configure":
            secret = sys.stdin.read().strip() if args.secret_stdin else getpass.getpass("请输入 AppSecret：").strip()
            result = test_draft_access(args.appid, secret)
            current_defaults = load_publish_defaults()
            defaults = normalize_publish_defaults({
                "author": args.author if args.author is not None else current_defaults["author"],
                "contentSourceUrl": args.source_url if args.source_url is not None else current_defaults["contentSourceUrl"],
                "needOpenComment": args.need_open_comment if args.need_open_comment is not None else current_defaults["needOpenComment"],
            })
            path = save_credentials(args.appid, secret, defaults)
            _print_json({**result, "path": str(path)})
            return 0
        if args.command == "test":
            _print_json(test_draft_access(args.appid))
            return 0
        if args.command == "publish":
            defaults = load_publish_defaults()
            if args.html_file:
                html_path = args.html_file.expanduser().resolve()
                document = html_path.read_text(encoding="utf-8")
                content = extract_article_content(document)
                title = args.title.strip() or _title_from_document(document)
                cover_path = find_cover(html_path.parent, args.cover)
            else:
                content_path = args.content_file.expanduser().resolve()
                content = content_path.read_text(encoding="utf-8")
                title = args.title.strip()
                cover_path = args.cover.expanduser().resolve() if args.cover else None
            if not cover_path:
                raise FileNotFoundError("没有找到封面，请使用 --cover 指定 PNG/JPEG 文件")
            cover_bytes, cover_mime, cover_extension = read_cover_file(cover_path)
            _print_json(publish_draft(
                title=title,
                author=args.author if args.author is not None else defaults["author"],
                digest=args.digest,
                content=content,
                content_source_url=args.source_url if args.source_url is not None else defaults["contentSourceUrl"],
                need_open_comment=args.need_open_comment if args.need_open_comment is not None else defaults["needOpenComment"],
                cover_bytes=cover_bytes,
                cover_mime=cover_mime,
                cover_extension=cover_extension,
            ))
            return 0
    except WeChatApiError as error:
        _print_json({"ok": False, "code": error.code, "error": str(error), "detail": error.detail})
        return 3
    except Exception as error:
        _print_json({"ok": False, "error": str(error)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
