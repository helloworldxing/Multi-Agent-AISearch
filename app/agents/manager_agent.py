from app.mcp.context import MCPContext


def plan(ctx: MCPContext) -> dict:
    """用于任务拆解的占位规划器。"""
    return {"steps": ["search", "summarize"]}
