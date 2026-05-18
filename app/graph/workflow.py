from typing import Callable

from app.mcp.context import MCPContext
from app.tools.registry import ToolRegistry


class SimpleWorkflow:
    """Minimal workflow placeholder for LangGraph integration."""

    def __init__(self, run_fn: Callable[[MCPContext], dict]) -> None:
        self._run_fn = run_fn

    def invoke(self, ctx: MCPContext) -> dict:
        return self._run_fn(ctx)


def build_workflow() -> SimpleWorkflow:
    tools = ToolRegistry.default()

    def _run(ctx: MCPContext) -> dict:
        search = tools.get("search")
        summarize = tools.get("summarize")
        docs = search(ctx)
        summary = summarize(ctx, docs)
        return {
            "request": ctx.request,
            "docs": docs,
            "summary": summary,
        }

    return SimpleWorkflow(_run)
