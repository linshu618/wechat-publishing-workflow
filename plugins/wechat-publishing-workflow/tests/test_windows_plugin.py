from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path
from urllib.request import Request, urlopen


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = PLUGIN_ROOT / "skills"
EDITOR_ROOT = SKILLS_ROOT / "wechat-html-editor"
PUBLISHER_ROOT = SKILLS_ROOT / "wechat-draft-publisher"
LAUNCHER = EDITOR_ROOT / "scripts" / "start_editor.ps1"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample article.html"
POWERSHELL = shutil.which("powershell.exe")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@unittest.skipUnless(os.name == "nt", "This plugin intentionally supports Windows only")
class WindowsPluginTests(unittest.TestCase):
    def test_editor_cli_help_uses_chinese(self) -> None:
        result = subprocess.run(
            [sys.executable, str(EDITOR_ROOT / "scripts" / "edit_html.py"), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("编辑并直接保存本地文章 HTML", result.stdout)
        self.assertIn("用法：", result.stdout)
        self.assertIn("选项:", result.stdout)
        self.assertNotIn("Edit and directly save", result.stdout)
        self.assertNotIn("usage:", result.stdout)

    def test_publisher_cli_help_uses_chinese(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PUBLISHER_ROOT / "scripts" / "wechat_draft.py"), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("将 HTML 发布到公众号草稿箱", result.stdout)
        self.assertIn("用法：", result.stdout)
        self.assertIn("命令:", result.stdout)
        self.assertNotIn("Publish HTML", result.stdout)
        self.assertNotIn("usage:", result.stdout)

    def test_editor_missing_file_error_uses_chinese(self) -> None:
        missing = Path(__file__).resolve().parent / "fixtures" / "不存在的文章.html"
        result = subprocess.run(
            [sys.executable, str(EDITOR_ROOT / "scripts" / "edit_html.py"), str(missing)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("找不到 HTML 文件", result.stderr)
        self.assertNotIn("HTML file not found", result.stderr)

    def test_plugin_bundles_both_skills(self) -> None:
        self.assertTrue((EDITOR_ROOT / "SKILL.md").is_file())
        self.assertTrue((PUBLISHER_ROOT / "SKILL.md").is_file())

    def test_editor_discovers_the_bundled_publisher(self) -> None:
        editor = load_module("bundled_wechat_editor", EDITOR_ROOT / "scripts" / "edit_html.py")
        self.assertEqual(editor.PUBLISHER_SCRIPT, PUBLISHER_ROOT / "scripts" / "wechat_draft.py")
        self.assertIsNotNone(editor.load_publisher())

    def test_cover_selection_uses_new_prefix_and_numeric_version(self) -> None:
        publisher = load_module("publisher_cover_versions", PUBLISHER_ROOT / "scripts" / "wechat_draft.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, modified in (
                ("公众号封面-v2.png", 400),
                ("公众号封面-v10.jpg", 200),
                ("公众号封面-v10.jpeg", 300),
                ("公众号封面-v100.gif", 500),
                ("08c-公众号封面-v999.png", 600),
                ("公众号封面.png", 700),
            ):
                path = root / name
                path.touch()
                os.utime(path, (modified, modified))
            self.assertEqual(publisher.find_cover(root), root / "公众号封面-v10.jpeg")

    def test_cover_selection_keeps_plain_name_and_explicit_override(self) -> None:
        publisher = load_module("publisher_cover_fallbacks", PUBLISHER_ROOT / "scripts" / "wechat_draft.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "08c-公众号封面-v1.png"
            legacy.touch()
            self.assertIsNone(publisher.find_cover(root))
            plain = root / "公众号封面.jpg"
            plain.touch()
            self.assertEqual(publisher.find_cover(root), plain)
            explicit = root / "自选封面.png"
            explicit.touch()
            self.assertEqual(publisher.find_cover(root, explicit), explicit)
            self.assertIsNone(publisher.find_cover(root, root / "不存在.png"))

    def test_editor_resolves_new_cover_name_in_the_article_directory(self) -> None:
        editor = load_module("editor_cover_resolution", EDITOR_ROOT / "scripts" / "edit_html.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            article = root / "任意文章.html"
            cover = root / "公众号封面-v3.png"
            cover.touch()
            server = editor.EditorServer(("127.0.0.1", 0), article, "test-token")
            try:
                self.assertEqual(server.resolve_cover(), cover)
                newer = root / "公众号封面-v4.jpg"
                newer.touch()
                self.assertEqual(server.resolve_cover(), newer)
                explicit = root / "自选封面.jpeg"
                explicit.touch()
                server.cover_path = explicit
                self.assertEqual(server.resolve_cover(), explicit)
            finally:
                server.server_close()

    def test_repeated_saves_keep_the_first_session_backup(self) -> None:
        editor = load_module("editor_session_backup", EDITOR_ROOT / "scripts" / "edit_html.py")
        original = "<!doctype html><html><body><article><p>原始正文</p></article></body></html>"
        first_edit = "<!doctype html><html><body><article><p>第一次修改</p></article></body></html>"
        second_edit = "<!doctype html><html><body><article><p>第二次修改</p></article></body></html>"
        with tempfile.TemporaryDirectory() as temporary:
            article = Path(temporary) / "自动保存测试.html"
            article.write_text(original, encoding="utf-8")
            token = "test-token"
            server = editor.EditorServer(("127.0.0.1", 0), article, token)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}/__wechat_editor/save"

            def save(document: str) -> dict[str, object]:
                request = Request(
                    url,
                    data=document.encode("utf-8"),
                    method="POST",
                    headers={
                        "Content-Type": "text/html; charset=utf-8",
                        "X-WeChat-Editor-Token": token,
                    },
                )
                with urlopen(request, timeout=5) as response:
                    return json.loads(response.read().decode("utf-8"))

            try:
                first_result = save(first_edit)
                second_result = save(second_edit)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

            self.assertEqual(article.read_text(encoding="utf-8"), second_edit)
            self.assertEqual(Path(str(article) + ".bak").read_text(encoding="utf-8"), original)
            self.assertTrue(first_result["backupCreated"])
            self.assertFalse(second_result["backupCreated"])

    def test_dpapi_round_trip_uses_the_current_windows_user(self) -> None:
        publisher = load_module("bundled_wechat_publisher", PUBLISHER_ROOT / "scripts" / "wechat_draft.py")
        sentinel = "codex-wechat-dpapi-round-trip"
        protected = publisher._dpapi("protect", sentinel)
        self.assertNotEqual(protected, sentinel)
        self.assertEqual(publisher._dpapi("unprotect", protected), sentinel)

    def test_publish_defaults_are_saved_per_account_without_plaintext_secret(self) -> None:
        publisher = load_module("publisher_defaults_save", PUBLISHER_ROOT / "scripts" / "wechat_draft.py")
        defaults = {
            "author": "默认作者",
            "contentSourceUrl": "https://example.com/source",
            "needOpenComment": True,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                mock.patch.object(publisher, "CONFIG_ROOT", root),
                mock.patch.object(publisher, "CONFIG_PATH", root / "credentials.json"),
                mock.patch.object(publisher, "LEGACY_CONFIG_PATH", root / "legacy.json"),
            ):
                publisher.save_credentials("wx-test-account", "secret-value", defaults)
                status = publisher.credential_status()
                raw = (root / "credentials.json").read_text(encoding="utf-8")

        self.assertTrue(status["configured"])
        self.assertEqual(status["appid"], "wx-test-account")
        self.assertEqual(status["defaults"], defaults)
        self.assertNotIn("secret-value", raw)

    def test_updating_publish_defaults_preserves_dpapi_secret(self) -> None:
        publisher = load_module("publisher_defaults_update", PUBLISHER_ROOT / "scripts" / "wechat_draft.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                mock.patch.object(publisher, "CONFIG_ROOT", root),
                mock.patch.object(publisher, "CONFIG_PATH", root / "credentials.json"),
                mock.patch.object(publisher, "LEGACY_CONFIG_PATH", root / "legacy.json"),
            ):
                publisher.save_credentials("wx-test-account", "secret-value")
                publisher.save_publish_defaults(
                    "wx-test-account",
                    {
                        "author": "新作者",
                        "contentSourceUrl": "https://example.com/new",
                        "needOpenComment": False,
                    },
                )
                appid, secret = publisher.load_credentials()
                status = publisher.credential_status()

        self.assertEqual(appid, "wx-test-account")
        self.assertEqual(secret, "secret-value")
        self.assertEqual(status["defaults"]["author"], "新作者")
        self.assertFalse(status["defaults"]["needOpenComment"])

    def test_publish_payload_includes_author_source_url_and_comment_default(self) -> None:
        publisher = load_module("publisher_payload_defaults", PUBLISHER_ROOT / "scripts" / "wechat_draft.py")
        captured: dict[str, object] = {}

        def capture_request(url: str, **kwargs):
            captured["url"] = url
            captured["payload"] = json.loads(kwargs["body"].decode("utf-8"))
            return {"media_id": "draft-media-id"}

        with (
            mock.patch.object(publisher, "resolve_credentials", return_value=("wx-test", "secret")),
            mock.patch.object(publisher, "get_access_token", return_value="access-token"),
            mock.patch.object(publisher, "upload_article_images", return_value="<p>正文</p>"),
            mock.patch.object(publisher, "upload_image", return_value={"media_id": "cover-media-id"}),
            mock.patch.object(publisher, "_request_json", side_effect=capture_request),
        ):
            result = publisher.publish_draft(
                title="测试标题",
                author="默认作者",
                digest="摘要",
                content="<p>正文</p>",
                content_source_url="https://example.com/source",
                need_open_comment=1,
                cover_bytes=b"cover",
                cover_mime="image/png",
                cover_extension="png",
            )

        article = captured["payload"]["articles"][0]
        self.assertEqual(article["author"], "默认作者")
        self.assertEqual(article["digest"], "摘要")
        self.assertEqual(article["content_source_url"], "https://example.com/source")
        self.assertEqual(article["need_open_comment"], 1)
        self.assertEqual(article["only_fans_can_comment"], 0)
        self.assertEqual(result["mediaId"], "draft-media-id")

    def test_publish_payload_omits_empty_digest(self) -> None:
        publisher = load_module("publisher_optional_digest", PUBLISHER_ROOT / "scripts" / "wechat_draft.py")
        for digest in ("", "   "):
            with (
                self.subTest(digest=digest),
                mock.patch.object(publisher, "resolve_credentials", return_value=("wx-test", "secret")),
                mock.patch.object(publisher, "get_access_token", return_value="access-token"),
                mock.patch.object(publisher, "upload_article_images", return_value="<p>正文</p>"),
                mock.patch.object(publisher, "upload_image", return_value={"media_id": "cover-media-id"}),
                mock.patch.object(publisher, "_request_json", return_value={"media_id": "draft-media-id"}) as request,
            ):
                publisher.publish_draft(
                    title="测试标题",
                    content="<p>正文</p>",
                    digest=digest,
                    cover_bytes=b"cover",
                    cover_mime="image/png",
                    cover_extension="png",
                )
                payload = json.loads(request.call_args.kwargs["body"].decode("utf-8"))
                self.assertNotIn("digest", payload["articles"][0])
                self.assertEqual(payload["articles"][0]["content"], "<p>正文</p>")

    def test_launcher_starts_an_article_from_a_path_with_spaces(self) -> None:
        self.assertIsNotNone(POWERSHELL)
        port = free_local_port()
        result = subprocess.run(
            [
                str(POWERSHELL),
                "-NoProfile",
                "-File",
                str(LAUNCHER),
                "-Article",
                str(FIXTURE),
                "-Port",
                str(port),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        process_id = int(payload["processId"])
        try:
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["port"], port)
            self.assertTrue(payload["health"]["draftPublisher"])
            with urlopen(payload["url"] + "__wechat_editor/health", timeout=5) as response:
                health = json.loads(response.read().decode("utf-8"))
            self.assertTrue(health["ok"])
            self.assertEqual(health["file"], FIXTURE.name)
        finally:
            subprocess.run(
                [
                    str(POWERSHELL),
                    "-NoProfile",
                    "-Command",
                    f"Stop-Process -Id {process_id} -Force -ErrorAction SilentlyContinue",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )


if __name__ == "__main__":
    unittest.main()
