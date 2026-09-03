# ChatGPT / MCP 图片能力核对报告

核对日期：2026-09-03。

## 结论

能实现“按语境检索私人表情包并在 ChatGPT 内看到图片”，但不能把“assistant 正文中的任意公网 Markdown 图片必定显示”视为官方保证。

最稳妥的组合是：

1. `structuredContent` 返回 `image_url`、metadata 和已经拼好的 Markdown。
2. server instructions 指导模型只在合适语境偶尔使用 Markdown，而非发送裸 URL。
3. 搜索/单图工具绑定 MCP Apps UI；UI 用 `<img>` 显示同一公开 URL，并在资源 CSP 中精确声明图片域名。

## 能力矩阵

| 返回方式 | 协议/官方支持 | 能否保证像普通聊天图片一样出现 | 本项目选择 |
| --- | --- | --- | --- |
| `structuredContent.image_url` | 是 | 否；它首先是模型可读数据 | 主数据通道 |
| `content` 中的 Markdown | 文本当然可返回 | 官方未承诺任意远程图在所有客户端渲染 | 尽力路径 |
| MCP `ImageContent`（base64） | MCP 规范支持 | 宿主如何呈现不由 MCP 规范规定；响应膨胀 | MVP 不默认使用 |
| `resource_link` 指向图片 | MCP 规范支持资源链接 | 资源链接不等于聊天图片 | 不采用 |
| MCP Apps `ui://` HTML | ChatGPT 官方支持 | 支持的 ChatGPT 客户端会把组件渲染在会话内 | **可靠降级** |

依据：

- OpenAI 对工具结果的正式字段定义为 `structuredContent`、`content`、`_meta`，其中 UI 通过 `_meta.ui.resourceUri` 关联：[Plugin reference](https://developers.openai.com/plugins/reference)。
- ChatGPT 实现 MCP Apps 标准；UI resource 使用 `text/html;profile=mcp-app`：[MCP Apps UI](https://developers.openai.com/plugins/build/chatgpt-ui)。
- MCP 规范允许工具返回 text、image、audio、resource links 和 embedded resources；它同时说明具体交互呈现由实现决定：[MCP Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)。

## CSP、域名和响应要求

MCP Apps 组件必须声明：

- `resourceDomains`：脚本、样式、图片等静态资源 origin。
- `connectDomains`：组件主动 fetch/XHR 的 origin。
- `frameDomains`：仅当嵌套 iframe 时使用。

本项目不从组件执行图片 fetch，只创建 `<img>`，并在服务器启动时从 `stickers.json` 解析所有 `image_url` origin 写进 `resourceDomains`。新增外部图片域名后必须重启 MCP 并在 ChatGPT 中 Refresh metadata。

OpenAI 文档没有公布一个“聊天正文远程图片域名白名单”，也没有承诺所有 Markdown 图片经同一种代理流程加载。因此下列是工程兼容性要求，不是假装存在的官方白名单：匿名 HTTPS、200 直返、正确图片 MIME、稳定 URL、无防盗链、无登录和临时签名。

## 本项目实际验证

在交付环境执行了：

- `pytest`：9 项通过。
- 官方 Python MCP SDK 客户端通过内存传输列出并调用 3 个默认工具。
- 官方 Python MCP SDK 客户端通过真实 Streamable HTTP `/mcp` 连接、列出工具并调用 `search_stickers`。
- 测试输入：`query=爱`、`emotion=安慰、亲昵`、`context=用户撒娇问我是不是不爱她了`、`limit=1`。
- 首项：`love_cat_001 / 永远很爱你猫猫`。
- 实际 GET `/media/love_cat_001.png`：`200 OK`、`Content-Type: image/png`、无重定向、9322 bytes。
- HTTP 下载文件与仓库源文件 SHA-256 一致：`08012b929521134fe4da1431f6f33239348d29e54caa5cf0462a14fa715b8760`。
- UI resource MIME 验证为 `text/html;profile=mcp-app`，工具的 `_meta.ui.resourceUri` 与 CSP `resourceDomains` 均通过协议测试。

## 尚需用户侧完成的一次验证

这个工作容器不能替用户修改 ChatGPT 的 Developer mode/Plugins，也没有用户的 Render 或域名账号，所以不能诚实声称已经在用户账号的 Android/Web 客户端完成最后一跳。

部署后按以下顺序完成最后验证：

1. 浏览器直接打开 `https://你的域名/media/love_cat_001.png`。
2. 用 MCP Inspector 调用 `search_stickers`。
3. 在 ChatGPT Plugins 开发者模式连接 `https://你的域名/mcp`。
4. 新开 Work 对话，`@老婆表情包` 后输入“你今天是不是不爱我了😾”。
5. 分别记录正文 Markdown 是否显示、MCP Apps 卡片是否显示。

即使第 5 步的正文 Markdown 在某一客户端不显示，卡片显示即证明可靠链路完成；这正是双通道设计存在的原因。

