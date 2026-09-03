from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("release_packager", REPOSITORY_ROOT / "scripts" / "package_release.py")
packager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packager)


class ReleasePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "source"
        for name in packager.RELEASE_FILES:
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPOSITORY_ROOT / name, destination)
        self.output = Path(self.temporary.name) / "dist"

    def test_only_allowlisted_files_are_packed(self) -> None:
        unwanted = (
            ".git/config", ".env", "credentials.json", "私人笔记.md",
            "plugins/wechat-publishing-workflow/tests/runtime/文章.html.bak",
            "plugins/wechat-publishing-workflow/skills/wechat-html-editor/scripts/__pycache__/edit_html.pyc",
        )
        for name in unwanted:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("不应进入发布包", encoding="utf-8")
        result = packager.build_release(self.root, self.output)
        with zipfile.ZipFile(result["archive"]) as archive:
            prefix = "wechat-publishing-workflow/"
            self.assertEqual(set(archive.namelist()), {prefix + name for name in packager.RELEASE_FILES} | {prefix + "release-manifest.json"})
            manifest = json.loads(archive.read(prefix + "release-manifest.json"))
            for name, expected_hash in manifest["files"].items():
                self.assertEqual(hashlib.sha256(archive.read(prefix + name)).hexdigest(), expected_hash)
        self.assertEqual(hashlib.sha256(Path(result["archive"]).read_bytes()).hexdigest(), result["sha256"])

    def test_missing_required_file_stops_packaging(self) -> None:
        (self.root / "LICENSE").unlink()
        with self.assertRaises(FileNotFoundError):
            packager.build_release(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_identical_inputs_produce_identical_archives(self) -> None:
        first = packager.build_release(self.root, self.output)
        second = packager.build_release(self.root, self.output)
        self.assertEqual(first["sha256"], second["sha256"])

    def test_changed_inputs_do_not_overwrite_existing_archive(self) -> None:
        first = packager.build_release(self.root, self.output)
        original = Path(first["archive"]).read_bytes()
        (self.root / "README.md").write_text("变更后的内容", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            packager.build_release(self.root, self.output)
        self.assertEqual(Path(first["archive"]).read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
