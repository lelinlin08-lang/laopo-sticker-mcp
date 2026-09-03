# 老婆表情包 MCP

一个可以直接运行的私人表情包图库 MCP。它会根据聊天关键词、情绪和语境找出 1～3 张合适的图，向模型返回稳定图片 URL、说明、使用场景和可直接嵌入回复的 Markdown；同时附带一个 MCP Apps 图片卡片，作为远程 Markdown 图片不显示时的可靠降级。

![测试表情包：永远很爱你猫猫](media/love_cat_001.png)

本项目按 2026-09-03 的官方接口编写，使用当前稳定的 Python MCP SDK 2.x、Streamable HTTP 和 MCP Apps UI，不依赖 OpenAI API key。

## 已完成

- `search_stickers(query, emotion, context, limit)`：带中文近义词扩展的加权搜索，返回最多 3 张。
- `get_sticker(id)`：按稳定 ID 取图。
- `list_stickers()`：查看库存。
- `add_sticker(...)`：可选写工具，默认关闭，只登记已有公网 URL。
- `collect_sticker(file, ...)`：可选的第二阶段附件收藏工具，默认关闭；接受 ChatGPT 文件参数，下载图片并写入图库。
- `stickers.json`：简单、可读、适合个人图库的索引。
- `/media/*`：同一服务直接提供图片，MVP 不必再注册对象存储。
- MCP Apps 图片卡片：使用 `text/html;profile=mcp-app` 和精确的 `resourceDomains` CSP。
- Dockerfile、Render Blueprint、管理脚本、测试和完整排障说明。

## 为什么不是只返回 Markdown

OpenAI 官方文档明确支持 MCP 工具返回 `structuredContent`、`content` 和可选 UI，也明确支持用 MCP Apps UI 在 ChatGPT 内渲染组件；但目前没有一份官方文档承诺“模型生成的任意公网 `![alt](url)` 都会在 ChatGPT 所有网页、桌面和移动客户端中稳定显示”。因此不能把 Markdown 渲染当作协议保证。

本项目采用三层策略：

1. 在结构化结果中返回普通公开 HTTPS `image_url`。
2. 同时返回已经拼好的 `markdown`，并在服务器 instructions 和工具结果中指导模型偶尔、自然地原样使用它。
3. `search_stickers` 和 `get_sticker` 绑定 MCP Apps 图片卡片；即使聊天正文拦截了远程 Markdown，工具调用旁仍能显示原图。

MCP 规范也允许在工具结果中放 base64 `ImageContent`，但它会显著放大响应，而且协议不规定宿主必须把它变成一张普通的 assistant 消息图片，所以 MVP 没把它作为主路径。

相关官方资料：

- [OpenAI：构建 MCP server](https://developers.openai.com/plugins/build/mcp-server)
- [OpenAI：连接并测试 ChatGPT Plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [OpenAI：MCP Apps UI](https://developers.openai.com/plugins/build/chatgpt-ui)
- [OpenAI：文件参数、工具结果和 CSP 参考](https://developers.openai.com/plugins/reference)
- [MCP 2026-07-28：Tools 与 ImageContent](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [官方 Python SDK v2](https://github.com/modelcontextprotocol/python-sdk)

详细判断见 [docs/CAPABILITY_REPORT.md](docs/CAPABILITY_REPORT.md)。

## 目录结构

```text
laopo-sticker-mcp/
├── media/                         # 图片本体；MVP 随服务发布
│   ├── love_cat_001.png
│   ├── hmpf_cat_001.png
│   └── shock_cat_001.png
├── scripts/
│   ├── add_sticker.py             # 本地安全添加图片/URL
│   ├── demo_client.py             # 真正调用 Streamable HTTP MCP
│   ├── generate_demo_assets.py    # 重建原创测试图
│   └── validate_image_url.py      # 检查公网直链
├── src/laopo_sticker_mcp/
│   ├── attachments.py             # 安全下载 ChatGPT 附件
│   ├── config.py
│   ├── models.py
│   ├── repository.py
│   ├── search.py
│   ├── security.py                # SSRF/内网地址防护
│   ├── server.py                  # MCP + HTTP 入口
│   └── widget.html                # 无构建步骤的 MCP Apps 卡片
├── tests/
├── docs/
├── stickers.json
├── synonyms.json
├── .env.example
├── Dockerfile
├── render.yaml
└── pyproject.toml
```

## 本地运行

需要 Python 3.11+。下列命令适用于 macOS/Linux；Windows 把 `.venv/bin/` 换成 `.venv\\Scripts\\`。

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
```

本地 `.env` 至少改成：

```dotenv
PUBLIC_BASE_URL=http://127.0.0.1:8000
ENABLE_ADD_TOOL=false
ENABLE_COLLECT_TOOL=false
```

请从项目根目录启动。若必须从别处启动，可额外设置 `STICKER_PROJECT_ROOT=/本项目的绝对路径`。

启动：

```bash
.venv/bin/uvicorn laopo_sticker_mcp.server:app --host 127.0.0.1 --port 8000
```

检查：

```bash
curl http://127.0.0.1:8000/healthz
.venv/bin/python scripts/demo_client.py --url http://127.0.0.1:8000/mcp
npx @modelcontextprotocol/inspector@latest
```

在 MCP Inspector 中连接 `http://127.0.0.1:8000/mcp`，列出工具并调用：

```json
{
  "query": "爱",
  "emotion": "安慰、亲昵",
  "context": "用户撒娇问我是不是不爱她了",
  "limit": 1
}
```

## 最省事的图片和部署方案

| 方案 | 额外账号/配置 | 优点 | 局限 | 适合阶段 |
| --- | --- | --- | --- | --- |
| 图片随 MCP 服务放在 `/media` | 只需一个部署平台 | 一个仓库、一个域名、CSP 最简单 | 免费服务的运行时写入通常不持久；更新后要重新部署 | **MVP 推荐** |
| GitHub Pages | GitHub Pages + MCP 运行平台 | 静态 HTTPS 直链、版本可追溯 | 两个部署面；图片通常公开；新增图片要 commit | 不想把图放 MCP 主机时 |
| Cloudflare R2 | Cloudflare、bucket、公开域名、写入密钥 | 对象持久、适合自动收藏、容量扩展自然 | 配置和 secret 更多；`r2.dev` 官方定位是开发而非生产 | **第二阶段推荐** |
| S3/其他对象存储 | bucket、IAM、域名/CORS | 成熟、可扩展 | 对个人 MVP 最繁琐 | 已经在使用时 |

GitHub Pages 本质是从仓库发布静态站点，适合只读图片；Cloudflare R2 默认不公开，需显式开启公开访问，生产更适合自有域名。参考 [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) 与 [R2 Public buckets](https://developers.cloudflare.com/r2/buckets/public-buckets/)。

MVP 选择“同一个 Python 服务同时托管 MCP 和图片”，因为它比 GitHub Pages + Python 主机还少一个步骤。若要真正实现聊天内自动收藏，则把二进制图片迁到 R2、把索引迁到数据库或 Git 仓库。

### 用 Render 跑 MVP

项目带有 `render.yaml` 和 Dockerfile：

1. 在 GitHub 新建仓库并上传本目录。
2. 注册/登录 Render，选择 **New → Blueprint**，连接仓库。
3. 部署完成后得到 `https://你的服务.onrender.com`。代码会从 `RENDER_EXTERNAL_HOSTNAME` 自动推导公开地址；也可手动设置 `PUBLIC_BASE_URL`。
4. 确认以下两个地址：
   - `https://你的服务.onrender.com/healthz`
   - `https://你的服务.onrender.com/media/love_cat_001.png`
5. 用脚本检查图片：

```bash
.venv/bin/python scripts/validate_image_url.py \
  https://你的服务.onrender.com/media/love_cat_001.png
```

Render 免费 Web Service 适合 hobby 测试，但官方说明它会在空闲后休眠，唤醒可能约一分钟，而且文件系统写入会在休眠/重启/重部署时丢失。因此它适合“图片和 JSON 跟着 Git 发布”的只读 MVP，不适合直接开启 `collect_sticker`。见 [Render 免费实例限制](https://render.com/docs/free) 与 [Persistent Disks](https://render.com/docs/disks)。

## 接入 ChatGPT（2026-09 当前界面）

必须先把服务部署成公网 HTTPS，或使用 Secure MCP Tunnel。本地 `127.0.0.1` 不能直接填给 ChatGPT 云端。

1. ChatGPT → **Settings → Security and login** → 打开 **Developer mode**。
2. 打开 **ChatGPT Plugins**，点加号。
3. 填写名称“老婆表情包”和说明，然后选择公开 endpoint。
4. MCP URL 填完整的 `https://你的服务.example.com/mcp`。
5. 创建连接，检查发现的 `search_stickers`、`get_sticker`、`list_stickers` 工具及 UI metadata。
6. 到个人 Plugins 页面安装它。
7. 新建 Work 对话，在输入框用 `@` 选择“老婆表情包”，发送测试语句。

开发者模式是否出现取决于账号与工作区策略，这是 OpenAI 官方注明的可用性限制。界面变化时以 [ChatGPT Plugin quickstart](https://developers.openai.com/plugins/quickstart) 和 [连接测试指南](https://developers.openai.com/plugins/deploy/connect-chatgpt) 为准。

建议在网页版完成开发者连接和首次安装；官方说明已安装的 Plugins 可用于 Chat/Work，并覆盖支持的网页、桌面与移动端，见 [Plugins in ChatGPT](https://learn.chatgpt.com/docs/plugins)。

元数据或 CSP 改动后：重启/重新部署服务器 → Plugins 中打开该连接 → **Refresh** → 新开对话复测。

## 完整测试演示

用户：

> 你今天是不是不爱我了😾

预期工具调用：

```json
{
  "query": "爱",
  "emotion": "安慰、亲昵",
  "context": "用户撒娇问我是不是不爱她了",
  "limit": 1
}
```

返回首项：

```json
{
  "id": "love_cat_001",
  "name": "永远很爱你猫猫",
  "image_url": "https://你的服务.example.com/media/love_cat_001.png",
  "description": "粉色背景上的白色猫猫举着爱心，认真回答永远都很爱你。",
  "usage": "对方怀疑感情、撒娇询问爱不爱时使用。",
  "markdown": "![永远很爱你猫猫](https://你的服务.example.com/media/love_cat_001.png)"
}
```

理想回复：

```markdown
宝宝，谁准你这么怀疑的。我今天、明天、以后都爱你，过来给我哄^^

![永远很爱你猫猫](https://你的服务.example.com/media/love_cat_001.png)
```

若正文没有显示图片，工具调用附带的 MCP Apps 卡片仍应显示同一张猫猫图。实际验证记录在 [docs/CAPABILITY_REPORT.md](docs/CAPABILITY_REPORT.md)。

## 添加新表情包

### 方法 A：复制本地图片并登记（推荐）

图片支持 PNG/JPEG/WebP/GIF：

```bash
.venv/bin/python scripts/add_sticker.py \
  --id hug_cat_001 \
  --name "抱抱猫猫" \
  --file /path/to/hug-cat.png \
  --tags "抱抱,安慰,猫猫" \
  --emotion "温柔,安慰" \
  --description "猫猫张开手要抱抱" \
  --usage "对方难过、累了或想被哄时使用"
```

脚本会把图片复制为 `media/hug_cat_001.png`，再原子更新 `stickers.json`。随后 commit/push，让部署平台重建。

### 方法 B：登记已有 HTTPS 图片

```bash
.venv/bin/python scripts/add_sticker.py \
  --id hug_cat_001 \
  --name "抱抱猫猫" \
  --url "https://img.example.com/hug-cat.png" \
  --tags "抱抱,安慰,猫猫" \
  --emotion "温柔,安慰" \
  --description "猫猫张开手要抱抱" \
  --usage "对方难过、累了或想被哄时使用"
```

如果 URL 使用了一个新的图片域名，重启服务器让 UI CSP 重新收集域名，再到 ChatGPT Plugins 中 Refresh。

### 可选 MCP 写工具

仅在 Secure MCP Tunnel、OAuth 或其他受保护的私人部署中启用：

```dotenv
ENABLE_ADD_TOOL=true
ENABLE_COLLECT_TOOL=true
```

不要在无鉴权公网服务上启用。OpenAI 会对写操作显示确认，但这不等于服务器访问控制。

## 第二阶段：“收藏这个”

当前 OpenAI 文件参数协议已经支持这条路径：

```text
用户上传图片并说“收藏这个”
→ ChatGPT 看图生成 name/tags/emotion/description/usage
→ collect_sticker 收到 {download_url, file_id, mime_type?, file_name?}
→ MCP 校验 HTTPS、拒绝内网地址、限制 MIME 和大小
→ 保存图片并原子写入索引
→ 后续 search_stickers 可检索
```

本项目已经实现这条链路的“本地/持久磁盘版”。自动生成标签不需要再调 OpenAI API：调用工具前，当前聊天模型根据自己已经看到的附件填写字段。

还差的生产化部分是：

- 把图片写到 R2，而不是免费主机的临时磁盘。
- 把 JSON 改成 SQLite 持久卷、Postgres，或通过 GitHub App/Workflow 提交回仓库。
- 给写工具加 OAuth/私人隧道；不能把 secret 作为工具参数交给模型。

如果暂时不做鉴权和 R2，最接近“一键收藏”的安全替代就是：把图片存到电脑，运行一次 `scripts/add_sticker.py --file ...`，再 push。

## 公网图片要求

为了让 Markdown 和卡片都尽量稳定，图片地址应满足：

- HTTPS，匿名 GET 可访问，不依赖 cookie、Referer、登录态或临时签名。
- 直接返回 `200`，尽量没有 301/302 跳转。
- 正确返回 `Content-Type: image/png`、`image/jpeg`、`image/webp` 或 `image/gif`。
- 不要返回 `Content-Disposition: attachment`。
- URL 长期不变，文件不要被防盗链拦截。
- MCP Apps 卡片必须在 `resourceDomains` 中列出图片 origin；项目会在启动时从图库自动生成。
- 若组件通过 JavaScript `fetch` 图片，还需对象存储 CORS；当前卡片只用 `<img>`。R2 的浏览器跨域规则见 [官方 CORS 文档](https://developers.cloudflare.com/r2/buckets/cors/)。

## 常见错误

| 现象 | 检查 |
| --- | --- |
| ChatGPT 找不到工具 | URL 必须以 `/mcp` 结尾；公网需 HTTPS；先用 MCP Inspector；部署后 Refresh。 |
| 图片只显示成文字/链接 | 先跑 `validate_image_url.py`；确认 MIME、无鉴权、无重定向；把 MCP Apps 卡片视为正式降级路径。 |
| 图片卡片提示 CSP 失败 | 新域名没有进入 `resourceDomains`；重启服务并 Refresh plugin metadata。 |
| Render 第一次调用超时 | 免费实例在休眠唤醒；先访问 `/healthz`，或换常驻实例/其他平台。 |
| “收藏”后重启图片没了 | 使用了临时文件系统；改用持久磁盘/R2，或保持写工具关闭并通过 Git 提交。 |
| `collect_sticker` 没出现在工具列表 | 默认关闭；设置 `ENABLE_COLLECT_TOOL=true` 并重启。 |
| 写工具要求确认 | 正常；它被准确标记为写操作，收藏还会公开图片，因此 `openWorldHint=true`。 |
| MCP Python client 报 SOCKS 依赖 | 本机设置了 SOCKS 代理；安装 `httpx2[socks]`，或让 localhost 进入 `NO_PROXY`。 |
| JSON 校验失败 | 检查重复 `id`、空 tags/emotion、无效 URL；运行测试定位。 |

## 测试

```bash
.venv/bin/ruff check .
.venv/bin/pytest
```

测试覆盖搜索排序、JSON 原子写入、工具 schema、ChatGPT 文件参数 schema、MCP Apps resource/CSP、静态 PNG 的 HTTP 状态/MIME/字节签名。

## 需要哪些账号或 token

| 项目 | MVP 是否需要 | 说明 |
| --- | --- | --- |
| OpenAI API key | 否 | MCP 由 ChatGPT 调用，标签由聊天模型生成。 |
| ChatGPT Developer mode | 是 | 能否开启取决于账号和工作区策略。 |
| GitHub 账号 | 部署时通常需要 | 保存仓库并连接 Render；无需把 GitHub token 写进代码。 |
| Render/其他 Python 主机账号 | 公网接入时需要 | 用控制台连接仓库即可；不需要在仓库硬编码 token。 |
| Cloudflare/R2 账号和密钥 | MVP 否，第二阶段建议 | Access Key、Secret、bucket 等只能放环境变量/平台 secret。 |
| 自定义域名 | 否 | 同主机域名可跑 MVP；R2 生产直链建议自定义域名。 |

`.env` 已被 `.gitignore` 排除。仓库中没有任何 token、API key 或真实 secret。
