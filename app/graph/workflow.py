from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.agents.chat_agent import chat
from app.agents.email_agent import send_email
from app.agents.planner_agent import plan
from app.agents.rag_agent import index_documents, retrieve
from app.agents.router_agent import classify
from app.agents.search_agent import search
from app.agents.writer_agent import write
from app.mcp.context import MCPContext


class ResearchState(TypedDict, total=False):
    ctx: MCPContext
    intent: str
    subqueries: list[str]
    # parallel sub-tasks append into these via reducer
    chunks: Annotated[list[dict], operator.add]
    subtask_progress: Annotated[list[dict], operator.add]
    document: str
    chat_response: str
    email_to: str
    email_sent: dict
    error: str


# ---------- single-shot nodes ----------

def _router_node(state: ResearchState) -> dict:
    intent = classify(state["ctx"])
    if intent == "email" and not state.get("email_to"):
        intent = "research"
    return {"intent": intent}


def _chat_node(state: ResearchState) -> dict:
    response = chat(state["ctx"])
    return {"chat_response": response}


def _planner_node(state: ResearchState) -> dict:
    subqueries = plan(state["ctx"])
    return {"subqueries": subqueries}


def _write_node(state: ResearchState) -> dict:
    chunks = state.get("chunks", [])
    document = write(state["ctx"], chunks)
    return {"document": document}


def _email_node(state: ResearchState) -> dict:
    try:
        result = send_email(
            to=state["email_to"],
            subject=f"研究报告: {state['ctx'].request}",
            content=state["document"],
        )
        return {"email_sent": result}
    except Exception as e:
        return {"error": f"邮件发送失败: {e}"}


# ---------- per-subtask node (executed in parallel via Send) ----------

def _subtask_node(state: dict) -> dict:
    """Independent search + index + retrieve for one sub-query.

    Reads ``ctx``, ``subquery`` and ``subquery_idx`` from the Send payload.
    Returns ``chunks`` (reducer-appended) and ``subtask_progress``.
    """
    ctx: MCPContext = state["ctx"]
    subquery: str = state["subquery"]
    idx: int = state["subquery_idx"]
    subdir = f"sub_{idx}"

    docs = search(ctx, query=subquery, max_results=8)
    if not docs:
        return {
            "chunks": [],
            "subtask_progress": [{
                "idx": idx, "subquery": subquery,
                "docs": 0, "chunks": 0,
            }],
        }

    info = index_documents(ctx, docs, subdir=subdir)
    chunks = retrieve(ctx, query=subquery, subdir=subdir, k_recall=10, k_final=4)

    for c in chunks:
        c["subquery"] = subquery
        c["subquery_idx"] = idx

    return {
        "chunks": chunks,
        "subtask_progress": [{
            "idx": idx,
            "subquery": subquery,
            "docs": len(docs),
            "indexed_chunks": info.get("chunks", 0),
            "chunks": len(chunks),
        }],
    }


# ---------- routing ----------

def _route_from_router(state: ResearchState) -> str:
    return "chat" if state.get("intent") == "chat" else "planner"


def _fan_out_subtasks(state: ResearchState):
    subqueries = state.get("subqueries") or []
    return [
        Send("subtask", {"ctx": state["ctx"], "subquery": q, "subquery_idx": i})
        for i, q in enumerate(subqueries)
    ]


def _route_after_write(state: ResearchState) -> str:
    if state.get("intent") == "email" and state.get("email_to"):
        return "email"
    return END


# ---------- graph ----------

def build_workflow() -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("router", _router_node)
    graph.add_node("chat", _chat_node)
    graph.add_node("planner", _planner_node)
    graph.add_node("subtask", _subtask_node)
    graph.add_node("write", _write_node)
    graph.add_node("email", _email_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router", _route_from_router, {"chat": "chat", "planner": "planner"}
    )
    graph.add_edge("chat", END)

    # planner fans out into N parallel subtask runs, then converges to write
    graph.add_conditional_edges("planner", _fan_out_subtasks, ["subtask"])
    graph.add_edge("subtask", "write")

    graph.add_conditional_edges(
        "write", _route_after_write, {"email": "email", END: END}
    )
    graph.add_edge("email", END)
    return graph.compile()
