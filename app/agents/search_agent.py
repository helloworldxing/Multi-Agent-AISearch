from __future__ import annotations

import os
from tavily import TavilyClient

from app.mcp.context import MCPContext


def search(ctx: MCPContext) -> list[dict]:
    """Broad-recall web search.

    Asks Tavily for full page content (raw_content) so that the downstream
    RAG pipeline has substantial text to chunk and index, rather than only
    the short snippets returned by default.
    """
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = client.search(
        query=ctx.request,
        search_depth="advanced",
        max_results=12,
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
