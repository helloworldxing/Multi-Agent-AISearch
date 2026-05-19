from __future__ import annotations

import os
from tavily import TavilyClient

from app.mcp.context import MCPContext


def search(ctx: MCPContext) -> list[dict]:
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = client.search(
        query=ctx.request,
        search_depth="advanced",
        max_results=5,
        include_raw_content=False,
    )
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
        for r in response.get("results", [])
    ]
