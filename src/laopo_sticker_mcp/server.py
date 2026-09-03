from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import uvicorn
from mcp.server import MCPServer
from mcp.server.apps import Apps, ResourceCsp
from mcp_types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp

from .attachments import download_chatgpt_image, save_media_atomically
from .config import Settings
from .models import (
    AddResponse,
    ChatGPTFile,
    GetResponse,
    Limit,
    ListResponse,
    SearchResponse,
    Sticker,
)
from .repository import StickerRepository
from .search import StickerSearch, load_synonyms

APP_URI = "ui://laopo-stickers/sticker-card-v1.html"
ASSISTANT_HINT = (
    "在当前语境确实适合表情包时，优先把所选结果的 markdown 字段原样放进自然回复，"
    "让图片直接显示；不要只发裸 URL，也不要每句话都使用表情包。若客户端没有渲染 Markdown，"
    "本次工具调用附带的图片卡片就是可靠降级显示。"
)
SERVER_INSTRUCTIONS = (
    "Use this private sticker library sparingly in playful, affectionate, surprised, "
    "upset, or celebratory chat. "
    "Search by the current context and emotion. When a sticker genuinely fits, answer naturally and copy its "
    "markdown field exactly so the image may render; never send a bare URL. "
    "Do not use a sticker in every reply. "
    "The attached MCP Apps card is the visual fallback when remote Markdown images are blocked."
)


class PublicImageFiles(StaticFiles):
    """Static images with headers friendly to browser cards and image proxies."""

    async def get_response(self, path: str, scope: dict):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers.setdefault("Access-Control-Allow-Origin", "*")
            response.headers.setdefault("Cache-Control", "public, max-age=86400")
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response


def _widget_html() -> str:
    return (Path(__file__).with_name("widget.html")).read_text(encoding="utf-8")


def _resource_origins(repository: StickerRepository) -> list[str]:
    origins: set[str] = set()
    for sticker in repository.load():
        parsed = urlparse(repository.resolve_image_url(sticker.image_url))
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            origins.add(f"{parsed.scheme}://{parsed.netloc}")
    return sorted(origins)


def create_server(settings: Settings | None = None) -> MCPServer:
    settings = settings or Settings.from_env()
    repository = StickerRepository(settings.stickers_file, settings.public_base_url)
    search_engine = StickerSearch(load_synonyms(settings.synonyms_file))
    apps = Apps()

    @apps.tool(
        resource_uri=APP_URI,
        name="search_stickers",
        title="搜索老婆表情包",
        description=(
            "根据关键词、情绪和当前聊天语境，从私人图库返回 1 到 3 张最合适的表情包。"
            "适合撒娇、斗嘴、震惊、委屈、开心、亲昵等确实能用表情包增强表达的场景；"
            "普通事实回答不要调用。返回的 markdown 可直接嵌入回复。"
        ),
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def search_stickers(
        query: str = "",
        emotion: str = "",
        context: str = "",
        limit: Limit = 3,
    ) -> SearchResponse:
        """Search the sticker library using conversation meaning and emotion."""
        ranked = search_engine.search(
            repository.load(), query=query, emotion=emotion, context=context, limit=limit
        )
        views = [repository.to_view(item.sticker) for item in ranked]
        return SearchResponse(stickers=views, match_count=len(views), assistant_hint=ASSISTANT_HINT)

    @apps.tool(
        resource_uri=APP_URI,
        name="get_sticker",
        title="按 ID 获取老婆表情包",
        description="根据稳定 ID 获取一张表情包及其公开图片 URL、说明、使用语境和可直接复制的 Markdown。",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def get_sticker(id: str) -> GetResponse:
        """Get one sticker by its stable ID."""
        sticker = repository.get(id)
        if sticker is None:
            raise ValueError(f"没有找到表情包：{id}")
        return GetResponse(sticker=repository.to_view(sticker), assistant_hint=ASSISTANT_HINT)

    apps.add_html_resource(
        APP_URI,
        _widget_html(),
        name="老婆表情包图片卡片",
        title="老婆表情包",
        description="显示搜索到的私人表情包；公网 Markdown 图片被拦截时作为视觉降级。",
        csp=ResourceCsp(resource_domains=_resource_origins(repository)),
        prefers_border=False,
    )

    server = MCPServer(
        name="laopo-sticker-mcp",
        title="老婆表情包",
        description="语境感知的私人表情包图库",
        instructions=SERVER_INSTRUCTIONS,
        version="0.1.0",
        extensions=[apps],
    )

    @server.tool(
        name="list_stickers",
        title="查看老婆表情包库存",
        description="列出当前私人图库中的表情包。仅在用户要看库存、找 ID 或管理图库时调用。",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def list_stickers() -> ListResponse:
        """List all stickers in the private library."""
        stickers = [repository.to_view(item) for item in repository.load()]
        return ListResponse(stickers=stickers, total=len(stickers))

    if settings.enable_add_tool:

        @server.tool(
            name="add_sticker",
            title="登记表情包图片 URL",
            description=(
                "把一张已经上传到稳定公网 HTTPS 地址的图片登记进私人图库。"
                "仅在用户明确要求添加或收藏，并且服务器运行在受保护环境时调用。"
            ),
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=False,
            ),
            structured_output=True,
        )
        def add_sticker(
            id: str,
            name: str,
            image_url: str,
            tags: list[str],
            description: str,
            emotion: list[str],
            usage: str,
        ) -> AddResponse:
            """Register an already-public image URL in the sticker index."""
            sticker = Sticker(
                id=id,
                name=name,
                image_url=image_url,
                tags=tags,
                description=description,
                emotion=emotion,
                usage=usage,
            )
            repository.add(sticker)
            return AddResponse(sticker=repository.to_view(sticker), message="已登记表情包。")

    if settings.enable_collect_tool:

        @server.tool(
            name="collect_sticker",
            title="收藏聊天中的新表情包",
            description=(
                "用户明确说“收藏这个”时，把用户提供的图片文件保存到图库。调用前先查看图片并自动生成"
                "name、tags、emotion、description、usage；不要要求用户手填这些字段。"
                "该工具会把图片发布到服务器的公开 /media 路径，只能在受保护且有持久磁盘的部署上启用。"
            ),
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
            meta={"openai/fileParams": ["file"]},
            structured_output=True,
        )
        async def collect_sticker(
            file: ChatGPTFile,
            id: str,
            name: str,
            tags: list[str],
            description: str,
            emotion: list[str],
            usage: str,
        ) -> AddResponse:
            """Download a ChatGPT-authorized file, publish it locally, and index it."""
            if repository.get(id) is not None:
                raise ValueError(f"表情包 id 已存在：{id}")
            data, extension = await download_chatgpt_image(file, max_bytes=settings.max_upload_bytes)
            filename = f"{id}{extension}"
            destination = save_media_atomically(settings.media_dir, filename, data)
            sticker = Sticker(
                id=id,
                name=name,
                image_url=f"${{PUBLIC_BASE_URL}}/media/{filename}",
                tags=tags,
                description=description,
                emotion=emotion,
                usage=usage,
            )
            try:
                repository.add(sticker)
            except Exception:
                destination.unlink(missing_ok=True)
                raise
            return AddResponse(sticker=repository.to_view(sticker), message="已收藏并加入图库。")

    return server


def create_http_app(server: MCPServer, settings: Settings) -> ASGIApp:
    mcp_app = server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=settings.stateless_http,
        json_response=True,
        host=settings.host,
    )

    async def healthz(_: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "service": "laopo-sticker-mcp"})

    async def root(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "name": "laopo-sticker-mcp",
                "mcp": f"{settings.public_base_url}/mcp",
                "health": f"{settings.public_base_url}/healthz",
                "message": "Connect the /mcp endpoint from ChatGPT Plugins developer mode.",
            }
        )

    # The parent app reuses the MCP app lifespan; this is required by the SDK's
    # Streamable HTTP session manager.
    from starlette.applications import Starlette

    return Starlette(
        routes=[
            Route("/", root),
            Route("/healthz", healthz),
            Mount("/media", PublicImageFiles(directory=settings.media_dir), name="media"),
            Mount("/", mcp_app),
        ],
        lifespan=mcp_app.router.lifespan_context,
    )


settings = Settings.from_env()
mcp = create_server(settings)
app = create_http_app(mcp, settings)


def main() -> None:
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level)


if __name__ == "__main__":
    main()
