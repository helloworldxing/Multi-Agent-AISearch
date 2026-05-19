from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.agents.search_agent import search
from app.agents.writer_agent import write
from app.mcp.context import MCPContext


class ResearchState(TypedDict):
    ctx: MCPContext
    docs: list[dict]
    document: str


def _search_node(state: ResearchState) -> ResearchState:
    docs = search(state["ctx"])
    return {**state, "docs": docs}


def _write_node(state: ResearchState) -> ResearchState:
    document = write(state["ctx"], state["docs"])
    return {**state, "document": document}


def build_workflow() -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("search", _search_node)
    graph.add_node("write", _write_node)
    graph.add_edge(START, "search")
    graph.add_edge("search", "write")
    graph.add_edge("write", END)
    return graph.compile()
