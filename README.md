# Codex 公众号工作台

**AI 写初稿，你来润色，一键送进公众号草稿箱。**

把选题和素材交给 Codex，让 AI 帮你生成文章、拟好标题、排好公众号版式。你在浏览器里润色内容，满意后点击创建草稿，再到公众号后台确认发布。

不用再把正文复制来复制去、到后台重新处理格式、逐张上传配图和封面，或给每篇文章重复填写标题、作者。`Wechat Publishing Workflow` 帮你把这些发布前的杂事接好，让精力留给内容本身。

```text
AI 生成文章与排版 → 你润色定稿 → 一键推送草稿箱 → 后台发布
```

## 从写文章，到发文章

### AI 先完成初稿

告诉 Codex 想写什么、手头有哪些素材、希望用什么语气。它帮你生成标题和正文，按公众号需要的格式排版，完成后打开可编辑页面。

### 你把文章改成自己的表达

直接在文章里改句子、补观点、核对事实。图片也能看着调整，替换、移动、缩放，选中后按 `Delete` 删除。修改会自动保存，按 `Ctrl+S` 也能立即保存。

### 定稿后，把发布准备一起做完

配置好公众号和默认信息后，标题会从文章中自动带入，作者复用已保存的设置。文章目录中的封面可以自动识别，正文图片与封面随草稿一起上传。

点击 `创建草稿`，文章就进入公众号草稿箱。最后去后台预览、确认、发布。

## 省下这些重复操作

| 发布前的杂事 | 工作台帮你完成 |
| --- | --- |
| 起标题、写初稿 | Codex 根据选题和素材生成标题与正文 |
| 调整公众号格式 | 生成公众号 HTML，推送时带入排版 |
| 复制正文、切换编辑器、重新粘贴 | 直接将润色后的文章写入草稿箱 |
| 上传正文配图和封面 | 发布器自动处理图片上传 |
| 在后台再填一遍标题、作者 | 自动带入文章标题和默认作者 |
| 重复设置原文链接、评论开关 | 自动加载已保存的发布习惯 |

封面可以用现成图片，也可以搭配 Codex 环境中可用的图像生成工具制作，再按[使用指南](plugins/wechat-publishing-workflow/README.md)放进文章目录。正文、HTML 和图片都留在本地，方便后续修改与复用。

## 装好，写第一篇

准备好 Windows 10 / 11、Python 3.10+ 和支持插件的 Codex。下载项目或解压发布包，进入包含 `.agents` 和 `plugins` 的项目根目录。

```powershell
python -m pip install -r ".\plugins\wechat-publishing-workflow\requirements.txt"
codex plugin marketplace add .
codex plugin add wechat-publishing-workflow@personal
```

安装完成后，新建一个 Codex 任务，从选题和素材开始。

```text
根据下面的主题和素材，帮我写一篇公众号文章，拟好标题。
使用 $wechat-html-editor 生成公众号排版，打开编辑器让我润色。
```

已有 HTML 也可以直接打开。

```text
使用 $wechat-html-editor 打开这份 HTML。
保留现有排版，让我在浏览器里修改正文、替换图片。
```

编辑和复制可以先用起来，推送草稿时再连接公众号。

## 第一次推送，记住常用设置

点击工具栏的 `推送到草稿箱`，填写公众号 AppID 和 AppSecret，再点 `保存账号设置`。

把默认作者、阅读原文链接和评论开关设好。以后推送时会自动带入这些信息，标题从文章中读取。确认封面后点击 `创建草稿`，再到公众号后台完成预览、原创设置和发布。

公众号需要具备草稿接口权限，并将当前公网 IP 加入白名单。配置方法、封面命名和常见问题都放在[使用指南](plugins/wechat-publishing-workflow/README.md)里。

## 两个 Skill，分工清楚

| Skill | 负责的事情 |
| --- | --- |
| `wechat-html-editor` | 生成和打开 HTML、直接编辑、自动保存、管理图片、复制排版、打开发布面板 |
| `wechat-draft-publisher` | 保存账号设置、检查连接、上传正文图片和封面、创建草稿 |

可以从写作开始，也可以把现成文章接进来。封面生成通过当前 Codex 环境提供的图像能力完成，编辑与草稿推送由这两个 Skill 衔接。

习惯在公众号后台继续编辑时，也可以点击 `复制到公众号`，复制带排版和图片的正文。

## 每篇文章都有自己的位置

没有指定保存路径时，新文章会放在当前工作目录下。

```text
公众号文章\YYYY-MM-DD-标题\标题.html
```

指定了路径就按你的安排保存。遇到同名文件，会增加 `-v2`、`-v3` 等版本号，保留已有内容。

## 继续开发

项目使用 Python、原生 JavaScript 和 CSS。编辑器、发布器与打包脚本都有明确目录，方便按需要调整。

```text
plugins/wechat-publishing-workflow/
  skills/wechat-html-editor/       文章编辑与界面
  skills/wechat-draft-publisher/   微信草稿接口
  tests/                          回归测试
scripts/package_release.py        生成可分发压缩包
```

运行测试与打包。

```powershell
python -m unittest discover -s .\plugins\wechat-publishing-workflow\tests -v
python .\scripts\package_release.py
```

发布包生成在 `dist`，包含逐文件校验清单和 SHA-256 校验文件。打包脚本按固定清单收录文件，自动排除运行副本、备份、缓存和个人配置。

欢迎带着实际的文章排版、使用场景或问题复现来交流，也欢迎提交改进。

## 开源协议

[MIT License](LICENSE) · [中文参考译文](LICENSE.zh-CN.md)
