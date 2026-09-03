#!/usr/bin/env python3
"""按固定清单创建可核验的预览包，不收集运行目录或个人配置。"""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import zipfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PREFIX = "plugins/wechat-publishing-workflow/"
ROOT_FILES = (
    ".agents/plugins/marketplace.json",
    ".gitignore",
    "LICENSE",
    "LICENSE.zh-CN.md",
    "README.md",
    "scripts/package_release.py",
)
PLUGIN_FILES = (
    ".codex-plugin/plugin.json",
    ".gitignore",
    "LICENSE",
    "LICENSE.zh-CN.md",
    "README.md",
    "requirements.txt",
    "skills/wechat-draft-publisher/SKILL.md",
    "skills/wechat-draft-publisher/agents/openai.yaml",
    "skills/wechat-draft-publisher/scripts/wechat_draft.py",
    "skills/wechat-html-editor/SKILL.md",
    "skills/wechat-html-editor/agents/openai.yaml",
    "skills/wechat-html-editor/assets/editor.css",
    "skills/wechat-html-editor/assets/editor.js",
    "skills/wechat-html-editor/scripts/edit_html.py",
    "skills/wechat-html-editor/scripts/start_editor.ps1",
    "tests/fixtures/sample article.html",
    "tests/test_windows_plugin.py",
    "tests/test_release_package.py",
)
RELEASE_FILES = tuple(sorted(ROOT_FILES + tuple(PLUGIN_PREFIX + name for name in PLUGIN_FILES)))


def collect_release_files(root: Path) -> dict[str, bytes]:
    root = root.resolve()
    result: dict[str, bytes] = {}
    for name in RELEASE_FILES:
        candidate = root / name
        if candidate.is_symlink() or not candidate.resolve().is_relative_to(root):
            raise ValueError(f"拒绝打包外部路径或符号链接：{name}")
        if not candidate.is_file():
            raise FileNotFoundError(f"发布清单中的文件不存在：{name}")
        result[name] = candidate.read_bytes()
    return result


def build_release(root: Path, output_dir: Path) -> dict[str, object]:
    files = collect_release_files(root)
    plugin = json.loads(files[PLUGIN_PREFIX + ".codex-plugin/plugin.json"].decode("utf-8"))
    name, version = str(plugin["name"]), str(plugin["version"])
    if name != "wechat-publishing-workflow" or not re.fullmatch(r"[A-Za-z0-9._+-]+", version):
        raise ValueError("插件名称或版本号不符合打包要求")
    manifest = {
        "formatVersion": 1,
        "plugin": name,
        "version": version,
        "channel": "preview",
        "files": {path: hashlib.sha256(data).hexdigest() for path, data in files.items()},
    }
    entries = dict(files)
    entries["release-manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, data in sorted(entries.items()):
            info = zipfile.ZipInfo(f"{name}/{path}", date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    data = stream.getvalue()
    with zipfile.ZipFile(BytesIO(data)) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != len(entries):
            raise RuntimeError("压缩包完整性检查失败")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{name}-{version}-preview.zip"
    checksum_path = archive_path.with_suffix(".zip.sha256")
    digest = hashlib.sha256(data).hexdigest()
    checksum = f"{digest}  {archive_path.name}\n".encode("ascii")
    for path, content in ((archive_path, data), (checksum_path, checksum)):
        if path.exists() and path.read_bytes() != content:
            raise FileExistsError(f"同名文件内容不同，拒绝覆盖，请指定新的输出目录：{path}")
    for path, content in ((archive_path, data), (checksum_path, checksum)):
        if not path.exists():
            with path.open("xb") as handle:
                handle.write(content)
    return {
        "archive": str(archive_path),
        "checksum": str(checksum_path),
        "sha256": digest,
        "sourceFileCount": len(files),
        "archiveEntryCount": len(entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="按固定清单生成干净预览包及 SHA-256 校验文件", add_help=False)
    parser._positionals.title = "位置参数"
    parser._optionals.title = "选项"
    parser.add_argument("-h", "--help", action="help", help="显示帮助信息并退出")
    parser.add_argument("--output-dir", metavar="输出目录", type=Path, default=REPOSITORY_ROOT / "dist", help="输出目录，默认为仓库内的 dist")
    args = parser.parse_args()
    try:
        result = build_release(REPOSITORY_ROOT, args.output_dir)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"打包失败：{error}\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
