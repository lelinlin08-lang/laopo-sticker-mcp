#!/usr/bin/env python3
"""Call the deployed MCP exactly like an MCP client would."""

from __future__ import annotations

import argparse
import asyncio
import json

from mcp import Client


async def run(url: str) -> None:
    async with Client(url) as client:
        listed = await client.list_tools()
        print("tools:", [tool.name for tool in listed.tools])
        result = await client.call_tool(
            "search_stickers",
            {
                "query": "爱",
                "emotion": "安慰、亲昵",
                "context": "用户撒娇问我是不是不爱她了",
                "limit": 1,
            },
        )
        print(json.dumps(result.structured_content, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp")
    args = parser.parse_args()
    asyncio.run(run(args.url))


if __name__ == "__main__":
    main()
