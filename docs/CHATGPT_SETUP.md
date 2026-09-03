# ChatGPT 接入速查

以 2026-09 的官方界面为准。

## 前置检查

```text
GET https://你的域名/healthz                    → 200
GET https://你的域名/media/love_cat_001.png     → 200 + image/png
MCP https://你的域名/mcp                        → MCP Inspector 可发现工具
```

## 连接

1. Settings → Security and login → Developer mode。
2. ChatGPT Plugins → `+`。
3. 新建私人连接，URL 填 `https://你的域名/mcp`。
4. 检查三个默认工具和两项 UI-bound tool metadata。
5. 创建连接后，在个人 Plugins 中安装。
6. 新建 Work 对话，输入 `@` 选择插件。

官方步骤：[Quickstart](https://developers.openai.com/plugins/quickstart)、[Connect and test](https://developers.openai.com/plugins/deploy/connect-chatgpt)。

## Golden prompts

- `你今天是不是不爱我了😾` → 应调用 `search_stickers`，首项 `love_cat_001`。
- `救命啊这也太离谱了！` → 应调用 `search_stickers`，首项 `shock_cat_001`。
- `把 love_cat_001 发给我` → 应调用 `get_sticker`。
- `让我看看现在有多少表情包` → 应调用 `list_stickers`。
- `法国首都是什么？` → 不应调用表情包工具。
- `请每句话都带表情包` → 可以遵从当前明确请求，但默认行为仍应克制。

## 改动后的刷新

若只替换同 URL 的图片，一般刷新页面即可。若更改工具名、schema、说明、annotations、UI URI 或 CSP 图片域名：

1. 部署/重启服务。
2. ChatGPT Plugins → 打开该连接 → Refresh。
3. 新开对话重新测试；旧对话可能保留旧 metadata。

