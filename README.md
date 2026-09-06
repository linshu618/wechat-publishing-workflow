# Codex 公众号工作台

**解决公众号文章排版麻烦、配图封面上传繁琐、发布信息重复填写的问题。**

文章写好之后，还有不少发布准备：调整版式和图片、复制正文、上传封面、填写作者和阅读原文链接。`Wechat Publishing Workflow` 把这些操作放在一个本地工作台里，支持编辑 HTML、复制公众号兼容格式，并将文章和图片一起保存到公众号草稿箱。

```text
打开文章 HTML → 调整文字与图片 → 复制到公众号或创建草稿 → 后台预览发布
```

## 它帮你省下哪些操作

| 发布前的问题 | 工作台如何处理 |
| --- | --- |
| 公众号排版麻烦，来回粘贴还要调整格式 | 本地查看和编辑 HTML，复制时整理为公众号兼容格式 |
| 图片位置、大小要反复调整 | 在页面中替换、移动、缩放和删除图片 |
| 正文配图和封面要逐一上传 | 创建草稿时处理正文图片和封面上传 |
| 每篇文章都要重复填写发布信息 | 带入文章标题，复用默认作者、原文链接和评论设置 |
| 修改后容易忘记保存 | 停止输入约 1 秒自动保存，也支持 Ctrl+S，首次保存保留备份 |

HTML 和图片保存在本地，方便继续修改和复用。可以复制正文到公众号后台，也可以连接账号后直接创建草稿；最终发布在公众号后台完成。

## 安装与开始

需要 Windows 10 / 11、Python 3.10+ 和支持插件的 Codex。

```powershell
git clone https://github.com/linshu618/wechat-publishing-workflow.git
cd wechat-publishing-workflow
python -m pip install -r ".\plugins\wechat-publishing-workflow\requirements.txt"
codex plugin marketplace add .
codex plugin add wechat-publishing-workflow@personal
```

也可以下载 ZIP，解压后进入包含 `.agents` 和 `plugins` 的项目根目录，再运行安装命令。

安装完成后，新建一个 Codex 任务，把文章 HTML 的路径交给它：

```text
使用 $wechat-html-editor 打开这份 HTML。
保留现有排版，让我在浏览器里修改正文、替换图片。
```

打开后直接编辑文章。选中图片可以调整大小、对齐方式和位置，也可以按 `Delete` 删除。修改会自动保存。

## 复制正文，或直接创建草稿

习惯在公众号后台继续编辑时，点击 `复制标题` 和 `复制到公众号`，将内容粘贴到后台后预览。

需要直接创建草稿时，点击 `推送到草稿箱`，填写公众号 AppID 和 AppSecret，再点 `保存账号设置`。账号需要具备草稿接口权限，并将当前公网 IP 加入白名单。

默认作者、阅读原文链接和评论开关只需设置一次，以后会自动带入。确认文章标题和封面后点击 `创建草稿`，正文图片和封面会随文章上传。随后到公众号后台预览、按需设置原创声明并发布。

封面命名、账号配置、图片操作和常见问题见[使用指南](plugins/wechat-publishing-workflow/README.md)。

## 文件保存在哪里

打开已有 HTML 时直接使用原文件。新建文章的保存位置按以下顺序确定：明确指定的文件路径、当前项目配置、当前工作目录。

没有指定路径或配置时，目录结构为：

```text
YYYY-MM-DD-标题\标题.html
```

需要统一收纳文章时，在当前工作目录创建 `.wechat-publishing.json`：

```json
{"article_dir": "公众号文章"}
```

相对目录以当前工作目录为基准，也支持绝对目录。默认路径重名时追加 `-v2`、`-v3`，明确指定的文件已存在时拒绝覆盖。

## 两个 Skill

| Skill | 负责的事情 |
| --- | --- |
| `wechat-html-editor` | HTML 文件管理、直接编辑、自动保存、图片调整、复制排版和发布面板 |
| `wechat-draft-publisher` | 保存账号设置、检查连接、上传正文图片和封面、创建草稿 |

## 开发与验证

项目使用 Python、原生 JavaScript 和 CSS。

```text
plugins/wechat-publishing-workflow/
  skills/wechat-html-editor/       文章编辑与界面
  skills/wechat-draft-publisher/   微信草稿接口
  tests/                          回归测试
scripts/package_release.py        发布包打包脚本
```

```powershell
python -m unittest discover -s .\plugins\wechat-publishing-workflow\tests -v
python .\scripts\package_release.py
```

发布包输出到 `dist`，包含逐文件校验清单和 SHA-256 校验文件。打包脚本按固定清单收录文件，排除运行副本、备份、缓存和个人配置。

欢迎提交实际排版问题、使用反馈和改进。

## 开源协议

[MIT License](LICENSE) · [中文参考译文](LICENSE.zh-CN.md)
