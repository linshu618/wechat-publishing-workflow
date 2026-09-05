import importlib.util
import json
from datetime import date
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/wechat-html-editor/scripts/create_article.py"
spec = importlib.util.spec_from_file_location("create_article", SCRIPT)
creator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(creator)


class ArticlePathTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def create(self, content="<h1>正文标题</h1>", **kwargs):
        return creator.create_article(content, project=self.root, day=date(2026, 9, 5), **kwargs)

    def test_default_and_collision_preserve_original(self):
        first = self.create()
        self.assertEqual(first, self.root / "2026-09-05-正文标题/正文标题.html")
        second = self.create("<h1>正文标题</h1><p>新内容</p>")
        self.assertEqual(second.name, "正文标题-v2.html")
        self.assertEqual(first.read_text(encoding="utf-8"), "<h1>正文标题</h1>")

    def test_relative_and_absolute_configuration(self):
        for directory in ["内容/待发布", str(self.root / "独立目录")]:
            (self.root / creator.CONFIG_NAME).write_text(json.dumps({"article_dir": directory}), encoding="utf-8")
            expected = (self.root / directory).resolve()
            self.assertEqual(self.create().parent.parent, expected)

    def test_explicit_path_bypasses_invalid_config_and_refuses_overwrite(self):
        (self.root / creator.CONFIG_NAME).write_text("broken", encoding="utf-8")
        path = self.create(output="指定/文章.html")
        self.assertEqual(path, self.root / "指定/文章.html")
        with self.assertRaises(FileExistsError):
            self.create(output=str(path))
        self.assertEqual(path.read_text(encoding="utf-8"), "<h1>正文标题</h1>")
        with self.assertRaises(ValueError):
            self.create()

    def test_invalid_configuration(self):
        for value in [[], {"article_dir": None}, {"article_dir": ""}]:
            (self.root / creator.CONFIG_NAME).write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.create()

    def test_title_precedence_and_windows_names(self):
        self.assertEqual(creator.article_title("<title>页面</title><h1>正文 <em>标题</em></h1>"), "正文 标题")
        self.assertEqual(creator.article_title("<h1>正文</h1>", "确认标题"), "确认标题")
        self.assertEqual(creator.article_title("<title>页面</title>"), "页面")
        self.assertEqual(creator.article_title("<p>内容</p>"), "未命名文章")
        self.assertEqual(creator.article_title("", "CON"), "_CON")
        self.assertEqual(creator.article_title("", "标题:? ."), "标题--")


if __name__ == "__main__":
    unittest.main()
