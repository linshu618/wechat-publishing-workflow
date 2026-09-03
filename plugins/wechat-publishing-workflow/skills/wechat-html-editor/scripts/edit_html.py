#!/usr/bin/env python3
"""为本地 HTML 文章注入可视化编辑器，并提供安全保存通道。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import mimetypes
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

MAXIMUM_BYTES = 50 * 1024 * 1024
MAXIMUM_JSON_BYTES = 55 * 1024 * 1024
MARKER = "wechat-html-editor-runtime"
SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS = SKILL_ROOT / "assets"
PUBLISHER_SCRIPT = SKILL_ROOT.parent / "wechat-draft-publisher" / "scripts" / "wechat_draft.py"


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


def parse_args() -> argparse.Namespace:
    parser = ChineseArgumentParser(description="编辑并直接保存本地文章 HTML 文件。")
    parser.add_argument("html_file", metavar="HTML文件", type=Path, help="文章 HTML 的绝对路径或相对路径")
    parser.add_argument("--port", metavar="端口", type=int, default=17863, help="本机端口，默认 17863")
    parser.add_argument("--open", action="store_true", help="在系统默认浏览器中打开编辑器")
    parser.add_argument("--cover", metavar="封面文件", type=Path, help="公众号草稿使用的默认 PNG/JPEG 封面")
    parser.add_argument("--token", help=argparse.SUPPRESS)
    return parser.parse_args()


def load_publisher():
    if not PUBLISHER_SCRIPT.is_file():
        return None
    spec = importlib.util.spec_from_file_location("wechat_draft_publisher", PUBLISHER_SCRIPT)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_content_root(document: str) -> bool:
    lowered = document.lower()
    return "<article" in lowered or 'id="article"' in lowered or "id='article'" in lowered or "<main" in lowered


def inject_editor(document: str, token: str) -> str:
    if f'id="{MARKER}"' in document:
        return document
    style = (ASSETS / "editor.css").read_text(encoding="utf-8")
    script = (ASSETS / "editor.js").read_text(encoding="utf-8")
    head_injection = f'\n<style id="{MARKER}-style" data-wechat-editor>{style}</style>\n'
    toolbar_injection = f'\n<div id="{MARKER}" data-wechat-editor></div>\n'
    script_injection = (
        f'\n<script id="{MARKER}-script" nonce="{token}" data-wechat-editor>\n'
        f'window.__WECHAT_EDITOR_TOKEN__ = {json.dumps(token)};\n{script}\n</script>\n'
    )
    if "</head>" in document.lower():
        index = document.lower().rfind("</head>")
        document = document[:index] + head_injection + document[index:]
    else:
        document = head_injection + document
    body_match = re.search(r"<body\b[^>]*>", document, flags=re.IGNORECASE)
    if body_match:
        index = body_match.end()
        document = document[:index] + toolbar_injection + document[index:]
    else:
        document = toolbar_injection + document
    if "</body>" in document.lower():
        index = document.lower().rfind("</body>")
        document = document[:index] + script_injection + document[index:]
    else:
        document += script_injection
    return document


class EditorServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], article_path: Path, token: str, cover_path: Path | None = None):
        super().__init__(address, EditorHandler)
        self.article_path = article_path
        self.article_directory = article_path.parent
        self.token = token
        self.write_lock = threading.Lock()
        self.backup_created = False
        self.publisher = load_publisher()
        self.cover_path = cover_path

    def resolve_cover(self) -> Path | None:
        if self.cover_path and self.cover_path.is_file():
            return self.cover_path
        if self.publisher:
            return self.publisher.find_cover(self.article_directory)
        return None


class EditorHandler(BaseHTTPRequestHandler):
    server: EditorServer

    def log_message(self, format_string: str, *args: object) -> None:
        sys.stdout.write("[%s] %s\n" % (self.log_date_time_string(), format_string % args))
        sys.stdout.flush()

    def send_bytes(
        self,
        status: int,
        payload: bytes,
        content_type: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        self.send_bytes(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        request = urlparse(self.path)
        if request.path == "/":
            try:
                source = self.server.article_path.read_text(encoding="utf-8")
                rendered = inject_editor(source, self.server.token).encode("utf-8")
                self.send_bytes(
                    200,
                    rendered,
                    "text/html; charset=utf-8",
                    {"Content-Security-Policy": f"script-src 'nonce-{self.server.token}'; connect-src 'self'"},
                )
            except Exception as error:  # pragma: no cover - 错误会直接返回给用户
                self.send_json(500, {"ok": False, "error": str(error)})
            return
        if request.path == "/__wechat_editor/health":
            stat = self.server.article_path.stat()
            self.send_json(200, {
                "ok": True,
                "file": self.server.article_path.name,
                "bytes": stat.st_size,
                "draftPublisher": bool(self.server.publisher),
            })
            return
        if request.path == "/__wechat_editor/wechat/config":
            if self.headers.get("X-WeChat-Editor-Token") != self.server.token:
                self.send_json(404, {"ok": False, "error": "未找到请求资源"})
                return
            if not self.server.publisher:
                self.send_json(503, {"ok": False, "available": False, "error": "未安装 wechat-draft-publisher 技能"})
                return
            try:
                cover = self.server.resolve_cover()
                self.send_json(200, {
                    "ok": True,
                    "available": True,
                    **self.server.publisher.credential_status(),
                    "coverName": cover.name if cover else "",
                })
            except Exception as error:
                self.send_json(400, {"ok": False, "available": True, "error": str(error)})
            return
        self.serve_article_asset(request.path)

    def serve_article_asset(self, request_path: str) -> None:
        relative = unquote(request_path).lstrip("/")
        candidate = (self.server.article_directory / relative).resolve()
        try:
            candidate.relative_to(self.server.article_directory.resolve())
        except ValueError:
            self.send_json(403, {"ok": False, "error": "已拒绝路径遍历请求"})
            return
        if not candidate.is_file():
            self.send_json(404, {"ok": False, "error": "未找到请求资源"})
            return
        mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_bytes(200, candidate.read_bytes(), mime)

    def do_POST(self) -> None:  # noqa: N802
        request = urlparse(self.path)
        if self.headers.get("X-WeChat-Editor-Token") != self.server.token:
            self.send_json(404, {"ok": False, "error": "未找到请求资源"})
            return
        if request.path.startswith("/__wechat_editor/wechat/"):
            self.handle_wechat_request(request.path)
            return
        if request.path != "/__wechat_editor/save":
            self.send_json(404, {"ok": False, "error": "未找到请求资源"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAXIMUM_BYTES:
            self.send_json(413, {"ok": False, "error": "HTML 文件为空或超过 50 MB"})
            return
        payload = self.rfile.read(length)
        if len(payload) != length:
            self.send_json(400, {"ok": False, "error": "请求正文不完整"})
            return
        try:
            document = payload.decode("utf-8")
        except UnicodeDecodeError:
            self.send_json(400, {"ok": False, "error": "HTML 必须为 UTF-8"})
            return
        if "<html" not in document.lower() or not find_content_root(document):
            self.send_json(400, {"ok": False, "error": "提交内容不是包含正文区域的 HTML 文档"})
            return
        if "data-wechat-editor" in document or MARKER in document:
            self.send_json(400, {"ok": False, "error": "编辑器运行代码未清理，拒绝覆盖原文件"})
            return
        article_path = self.server.article_path
        backup_path = Path(str(article_path) + ".bak")
        with self.server.write_lock:
            temporary_path: Path | None = None
            try:
                backup_created = False
                if not self.server.backup_created:
                    shutil.copy2(article_path, backup_path)
                    self.server.backup_created = True
                    backup_created = True
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", newline="", delete=False, dir=article_path.parent,
                    prefix=article_path.name + ".", suffix=".tmp"
                ) as temporary:
                    temporary.write(document)
                    temporary.flush()
                    os.fsync(temporary.fileno())
                    temporary_path = Path(temporary.name)
                os.replace(temporary_path, article_path)
                self.send_json(200, {
                    "ok": True,
                    "bytes": article_path.stat().st_size,
                    "backup": backup_path.name,
                    "backupCreated": backup_created,
                })
            except Exception as error:  # pragma: no cover - 错误会直接返回给用户
                if temporary_path and temporary_path.exists():
                    temporary_path.unlink()
                self.send_json(500, {"ok": False, "error": str(error)})

    def read_json_body(self) -> dict[str, object]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAXIMUM_JSON_BYTES:
            raise ValueError("请求为空或超过 55 MB")
        payload = self.rfile.read(length)
        if len(payload) != length:
            raise ValueError("请求正文不完整")
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("请求不是有效的 UTF-8 JSON") from error
        if not isinstance(value, dict):
            raise ValueError("请求必须是 JSON 对象")
        return value

    def handle_wechat_request(self, request_path: str) -> None:
        publisher = self.server.publisher
        if not publisher:
            self.send_json(503, {"ok": False, "error": "未安装 wechat-draft-publisher 技能"})
            return
        try:
            body = self.read_json_body()
            appid = str(body.get("appid") or "").strip()
            secret = str(body.get("secret") or "").strip()
            if request_path == "/__wechat_editor/wechat/config":
                if not appid:
                    raise ValueError("请输入 AppID")
                defaults = publisher.normalize_publish_defaults(body.get("defaults"))
                result = publisher.test_draft_access(appid, secret)
                config_path = (
                    publisher.save_credentials(appid, secret, defaults)
                    if secret
                    else publisher.save_publish_defaults(appid, defaults)
                )
                self.send_json(200, {**result, "path": str(config_path)})
                return
            if request_path == "/__wechat_editor/wechat/test":
                self.send_json(200, publisher.test_draft_access(appid, secret))
                return
            if request_path == "/__wechat_editor/wechat/draft":
                cover_data = str(body.get("coverData") or "")
                if cover_data:
                    cover_bytes, cover_mime, cover_extension = publisher.decode_cover_data(cover_data)
                else:
                    cover = self.server.resolve_cover()
                    if not cover:
                        raise FileNotFoundError("没有找到封面，请在窗口中选择 PNG/JPEG 封面")
                    cover_bytes, cover_mime, cover_extension = publisher.read_cover_file(cover)
                result = publisher.publish_draft(
                    title=str(body.get("title") or ""),
                    author=str(body.get("author") or ""),
                    digest=str(body.get("digest") or ""),
                    content=str(body.get("content") or ""),
                    content_source_url=str(body.get("contentSourceUrl") or ""),
                    need_open_comment=body.get("needOpenComment", True),
                    cover_bytes=cover_bytes,
                    cover_mime=cover_mime,
                    cover_extension=cover_extension,
                    appid=appid,
                    secret=secret,
                )
                self.send_json(200, result)
                return
            self.send_json(404, {"ok": False, "error": "未找到请求资源"})
        except Exception as error:  # pragma: no cover - 错误会直接返回给用户
            self.send_json(400, {
                "ok": False,
                "code": getattr(error, "code", None),
                "error": str(error),
                "detail": getattr(error, "detail", None),
            })


def main() -> int:
    args = parse_args()
    article_path = args.html_file.expanduser().resolve()
    if not article_path.is_file() or article_path.suffix.lower() not in {".html", ".htm"}:
        print(f"错误：找不到 HTML 文件：{article_path}", file=sys.stderr)
        return 2
    try:
        source = article_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print("错误：HTML 文件必须使用 UTF-8 编码。", file=sys.stderr)
        return 2
    if not find_content_root(source):
        print("错误：找不到 <article>、#article 或 <main> 正文根节点。", file=sys.stderr)
        return 2
    token = args.token or secrets.token_urlsafe(24)
    cover_path = args.cover.expanduser().resolve() if args.cover else None
    if cover_path and not cover_path.is_file():
        print(f"错误：找不到封面文件：{cover_path}", file=sys.stderr)
        return 2
    try:
        server = EditorServer(("127.0.0.1", args.port), article_path, token, cover_path)
    except OSError as error:
        print(f"错误：无法监听 127.0.0.1:{args.port}：{error}", file=sys.stderr)
        return 3
    url = f"http://127.0.0.1:{args.port}/"
    print(f"EDITOR_URL={url}")
    print(f"ARTICLE_FILE={article_path}")
    sys.stdout.flush()
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
