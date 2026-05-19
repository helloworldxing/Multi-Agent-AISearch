from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.agents.chat_agent import chat
from app.agents.email_agent import send_email
from app.agents.router_agent import classify
from app.agents.search_agent import search
from app.agents.writer_agent import write
from app.mcp.context import MCPContext


class ResearchState(TypedDict, total=False):
    ctx: MCPContext
    intent: str
    docs: list[dict]
    document: str
    chat_response: str
    email_to: str
    email_sent: dict
    error: str


def _router_node(state: ResearchState) -> ResearchState:
    intent = classify(state["ctx"])
    if intent == "email" and not state.get("email_to"):
        intent = "research"
    return {**state, "intent": intent}


def _chat_node(state: ResearchState) -> ResearchState:
    response = chat(state["ctx"])
    return {**state, "chat_response": response}


def _search_node(state: ResearchState) -> ResearchState:
    docs = search(state["ctx"])
    return {**state, "docs": docs}


def _write_node(state: ResearchState) -> ResearchState:
    document = write(state["ctx"], state["docs"])
    return {**state, "document": document}


def _email_node(state: ResearchState) -> ResearchState:
    try:
        result = send_email(
            to=state["email_to"],
            subject=f"研究报告: {state['ctx'].request}",
            content=state["document"],
        )
        return {**state, "email_sent": result}
    except Exception as e:
        return {**state, "error": f"邮件发送失败: {e}"}


def _route_from_router(state: ResearchState) -> str:
    return "chat" if state.get("intent") == "chat" else "search"


def _route_after_write(state: ResearchState) -> str:
    if state.get("intent") == "email" and state.get("email_to"):
        return "email"
    return END


def build_workflow() -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("router", _router_node)
    graph.add_node("chat", _chat_node)
    graph.add_node("search", _search_node)
    graph.add_node("write", _write_node)
    graph.add_node("email", _email_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router", _route_from_router, {"chat": "chat", "search": "search"}
    )
    graph.add_edge("chat", END)
    graph.add_edge("search", "write")
    graph.add_conditional_edges(
        "write", _route_after_write, {"email": "email", END: END}
    )
    graph.add_edge("email", END)
    return graph.compile()
