---
name: wechat-draft-publisher
description: "当 Windows 用户明确要求测试公众号草稿接口、安全保存凭据、上传正文图片或封面，或从准备好的本地 HTML 创建草稿时使用。"
---

# 公众号草稿箱发布器

使用 `scripts/wechat_draft.py` 执行确定性的公众号接口操作。不要在某篇文章专用的服务器中重新实现这套接口流程。

## 运行要求

- Windows 10 或 Windows 11，并安装 PowerShell 和 Python 3.10 或更高版本。
- 发布图片前，安装插件根目录 `requirements.txt` 中的依赖。
- 公众号必须拥有草稿接口权限、有效的 AppID 和 AppSecret，并把当前公网 IP 加入白名单。
- 从 Codex 加载的技能路径解析本技能目录。禁止假设用户名或安装位置。

## 工作流程

1. 确认准确的文章 HTML 和封面图片。不能只根据当前浏览器标签页推断另一篇文章。
2. 运行 `status`，检查当前 Windows 用户是否已经保存加密凭据。
3. 缺少凭据时，运行 `configure --appid <APPID>`，通过标准输入或交互提示提供 AppSecret。不得把 AppSecret 写进命令行、源文件、文章、日志或聊天回复。
4. 某个账号首次发布前，或者凭据、IP 权限发生变化后，运行 `test`。
5. 只有用户明确要求创建草稿时才能运行 `publish`。测试接口权限不代表用户授权创建草稿。
6. 返回并报告草稿的 `media_id`。不得声称文章已经公开发布，本技能只负责创建草稿。

## 命令

```powershell
$publisher = Join-Path $skillRoot 'scripts\wechat_draft.py'
python $publisher status
python $publisher configure --appid 'wx...' --author '默认作者' --source-url 'https://example.com/article' --open-comment
python $publisher test
python $publisher publish --html-file 'C:\文章\article.html' --cover 'C:\图片\cover.png' --title '文章标题' --author '作者' --digest '摘要'
```

`publish` 可以接收 `--html-file`，从 `#article`、`<article>` 或 `<main>` 提取正文；也可以接收 `--content-file`，读取一段 HTML 正文片段。使用 `--html-file` 且省略 `--cover` 时，脚本会先在文章旁边查找最新的 `公众号封面-v*.png/jpg/jpeg`，再查找 `公众号封面.png/jpg/jpeg`。

`$skillRoot` 必须是包含当前 `SKILL.md` 的绝对目录，从 Codex 已解析的技能路径中取得。

## 凭据处理

- 凭据保存在 `%LOCALAPPDATA%\wechat-draft-publisher\credentials.json`。
- 使用 Windows DPAPI 为当前 Windows 用户加密 AppSecret。
- 任何情况下都不能降级为明文保存凭据。
- 如果发现旧版 `%LOCALAPPDATA%\wechat-html-editor\credentials.json`，自动迁移其中的凭据。
- 配置文件版本 2 可以按当前 AppID 保存默认作者、默认阅读原文链接和默认评论开关。更新这些默认值时不得破坏或暴露已加密的 AppSecret。
- `40164` 表示 IP 白名单问题，`48001` 表示缺少草稿接口权限，`40125` 表示 AppSecret 无效或已重置。

## 内容要求

- 标题和 HTML 正文不能为空。
- 标题最多 64 个字符，作者最多 16 个字符，摘要最多 120 个字符。
- 摘要为可选项；省略或留空时不发送 `digest` 字段，交由微信按默认规则处理。命令行仍支持 `--digest` 显式指定摘要。
- 阅读原文链接可以为空；填写时必须是有效的 HTTP 或 HTTPS 地址，UTF-8 编码后不能超过 1KB。
- 评论开关通过 `need_open_comment` 传给微信接口，`1` 表示开启，`0` 表示关闭。`only_fans_can_comment` 保持为 `0`。
- 正文图片只接受 PNG/JPEG 数据网址，或现有的 `mmbiz.qpic.cn`、`mmbiz.qlogo.cn` 地址。调用脚本前，应把浏览器中的本地图片转换成数据网址。
- 通过 `media/uploadimg` 上传正文图片，把封面上传为永久图片素材，最后调用 `draft/add`。
- 权限测试、凭据保存或内容验证失败时，不得创建草稿。
- 微信草稿接口没有原创声明字段，原创必须在公众号后台人工完成。

## 集成方式

`wechat-html-editor` 会从相邻的本技能中动态加载 `scripts/wechat_draft.py`，再通过编辑器受本机令牌保护的接口调用其中的功能。发布逻辑必须集中保留在这里，作为唯一实现来源。
