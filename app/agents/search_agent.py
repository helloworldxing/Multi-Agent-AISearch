from __future__ import annotations

import os
from typing import Optional

from tavily import TavilyClient

from app.mcp.context import MCPContext


def search(
    ctx: MCPContext, query: Optional[str] = None, max_results: int = 8
) -> list[dict]:
    """宽召回网页搜索。

    ``query`` 默认取 ``ctx.request``；在并行子任务检索时传入显式值。
    """
    actual_query = (query or ctx.request).strip()
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = client.search(
        query=actual_query,
        search_depth="advanced",
        max_results=max_results,
        include_raw_content=True,
    )
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
            "raw_content": r.get("raw_content") or r.get("content", ""),
        }
        for r in response.get("results", [])
    ]
