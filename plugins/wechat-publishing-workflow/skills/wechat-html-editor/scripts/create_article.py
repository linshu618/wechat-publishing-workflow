"""Create an article using project path preferences without overwriting files."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup


CONFIG_NAME = ".wechat-publishing.json"


def project_path(root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def article_title(content: str, title: str = "") -> str:
    if not title.strip():
        soup = BeautifulSoup(content, "html.parser")
        heading = soup.find("h1")
        title = heading.get_text(" ", strip=True) if heading else ""
        if not title.strip() and soup.title:
            title = soup.title.get_text(" ", strip=True)
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", title.strip()).rstrip(" .")
    title = title or "未命名文章"
    if re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³]", title.split(".")[0], re.I):
        title = "_" + title
    return title


def create_article(content: str, *, project: Path, title: str = "", output: str | None = None,
                   day: date | None = None) -> Path:
    root = project.resolve()
    if output is not None:
        destination = project_path(root, output)
        if destination.suffix.lower() not in {".html", ".htm"}:
            raise ValueError("指定保存路径必须是 .html 或 .htm 文件")
    else:
        config_file = root / CONFIG_NAME
        config = json.loads(config_file.read_text(encoding="utf-8-sig")) if config_file.exists() else {}
        if not isinstance(config, dict):
            raise ValueError("项目配置必须是 JSON 对象")
        directory = config.get("article_dir", ".")
        if not isinstance(directory, str) or not directory.strip():
            raise ValueError("article_dir 必须是非空路径字符串")
        name = article_title(content, title)
        destination = project_path(root, directory) / f"{day or date.today()}-{name}" / f"{name}.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    candidate = destination
    version = 2
    while True:
        try:
            with candidate.open("x", encoding="utf-8", newline="") as handle:
                handle.write(content)
            return candidate
        except FileExistsError:
            if output is not None:
                raise FileExistsError(f"指定文件已存在，拒绝覆盖：{destination}") from None
            candidate = destination.with_name(f"{destination.stem}-v{version}{destination.suffix}")
            version += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="按项目配置新建公众号 HTML，不覆盖已有文件")
    parser.add_argument("--source", required=True, type=Path, help="已生成的 UTF-8 HTML 内容文件")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="项目根目录，默认当前工作目录")
    parser.add_argument("--title", default="", help="已确认标题；未指定时提取 h1，再提取 title")
    parser.add_argument("--output", help="明确指定的 HTML 保存路径，优先于项目配置")
    args = parser.parse_args()
    try:
        result = create_article(args.source.read_text(encoding="utf-8-sig"), project=args.project,
                                title=args.title, output=args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"创建失败：{error}\n")
    print(json.dumps({"path": str(result)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
