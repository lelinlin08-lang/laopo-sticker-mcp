from __future__ import annotations

from dataclasses import replace

import pytest
from mcp import Client

from laopo_sticker_mcp.server import APP_URI, create_server


@pytest.mark.asyncio
async def test_tools_and_search_result(settings) -> None:
    server = create_server(settings)
    async with Client(server) as client:
        listed = await client.list_tools()
        assert [tool.name for tool in listed.tools] == ["search_stickers", "get_sticker", "list_stickers"]
        search_tool = next(tool for tool in listed.tools if tool.name == "search_stickers")
        assert search_tool.meta["ui"]["resourceUri"] == APP_URI
        assert search_tool.output_schema["type"] == "object"

        result = await client.call_tool(
            "search_stickers",
            {
                "query": "爱",
                "emotion": "安慰、亲昵",
                "context": "用户撒娇问我是不是不爱她了",
                "limit": 1,
            },
        )
        assert result.is_error is False
        assert result.structured_content["stickers"][0]["id"] == "love_cat_001"
        assert result.structured_content["stickers"][0]["markdown"].startswith("![")


@pytest.mark.asyncio
async def test_widget_resource_and_csp(settings) -> None:
    server = create_server(settings)
    async with Client(server) as client:
        resources = await client.list_resources()
        resource = next(item for item in resources.resources if str(item.uri) == APP_URI)
        assert resource.mime_type == "text/html;profile=mcp-app"
        assert "http://testserver" in resource.meta["ui"]["csp"]["resourceDomains"]
        result = await client.read_resource(APP_URI)
        assert "ui/notifications/tool-result" in result.contents[0].text


@pytest.mark.asyncio
async def test_optional_write_tools_and_file_contract(settings) -> None:
    enabled = replace(settings, enable_add_tool=True, enable_collect_tool=True)
    server = create_server(enabled)
    async with Client(server) as client:
        listed = await client.list_tools()
        by_name = {tool.name: tool for tool in listed.tools}
        assert {"add_sticker", "collect_sticker"} <= by_name.keys()
        collect = by_name["collect_sticker"]
        assert collect.meta["openai/fileParams"] == ["file"]
        file_schema = collect.input_schema["$defs"]["ChatGPTFile"]
        assert set(file_schema["properties"]) == {"download_url", "file_id", "mime_type", "file_name"}
        assert set(file_schema["required"]) == {"download_url", "file_id"}
