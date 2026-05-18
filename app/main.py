from app.graph.workflow import build_workflow
from app.mcp.context import MCPContext


def run() -> None:
    """Entry point for local runs."""
    ctx = MCPContext.new("AI research request")
    graph = build_workflow()
    result = graph.invoke(ctx)
    print(result)


if __name__ == "__main__":
    run()
