from __future__ import annotations

import os
from typing import Optional

from tavily import TavilyClient

from app.mcp.context import MCPContext


def search(ctx: MCPContext, query: Optional[str] = None, max_results: int = 8) -> list[dict]:
    """Broad-recall web search.

    ``query`` defaults to ``ctx.request``; pass an explicit value when running
    a per-subtask search in parallel research mode.
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
