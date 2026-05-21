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
    # 迭代与控制参数
    run_id: int
    expected_subtasks: int
    iteration: int
    max_iterations: int
    review: dict
    review_feedback: str
    # 并行子任务通过 reducer 追加到这些字段
    chunks: Annotated[list[dict], operator.add]
    subtask_progress: Annotated[list[dict], operator.add]
    document: str
    chat_response: str
    email_to: str
    email_sent: dict
    error: str


# ---------- 单步节点 ----------


def _router_node(state: ResearchState) -> dict:
    intent = classify(state["ctx"])
    if intent == "email" and not state.get("email_to"):
        intent = "research"
    # 默认循环设置（可由调用方覆盖）
    return {
        "intent": intent,
        "run_id": state.get("run_id", 0),
        "expected_subtasks": state.get("expected_subtasks", 0),
        "iteration": state.get("iteration", 0),
        "max_iterations": state.get("max_iterations", 2),
        "review": state.get("review", {}),
        "review_feedback": state.get("review_feedback", ""),
    }


def _chat_node(state: ResearchState) -> dict:
    response = chat(state["ctx"])
    return {"chat_response": response}


def _planner_node(state: ResearchState) -> dict:
    subqueries = plan(state["ctx"])
    return {
        "subqueries": subqueries,
        "expected_subtasks": len(subqueries),
        "run_id": state.get("run_id", 0) + 1,
    }


def _orchestrator_node(state: ResearchState) -> dict:
    """轻量协调节点。

    保持显式节点，便于工作流可视化控制点，
    并支持迭代回路（review -> replan -> orchestrator）。
    """
    return {}


def _write_node(state: ResearchState) -> dict:
    chunks = state.get("chunks", [])
    document = write(state["ctx"], chunks)
    return {"document": document}


def _reviewer_node(state: ResearchState) -> dict:
    """启发式审阅：给出 pass/fail 并提供可执行反馈。

    保持工作流自包含（不额外调用 LLM），同时提供明确的迭代回路。
    """
    doc = (state.get("document") or "").strip()
    issues: list[str] = []

    required_headings = [
        "## 摘要",
        "## 背景与动机",
        "## 关键发现",
        "## 详细分析",
        "## 结论与展望",
        "## 参考来源",
    ]
    for h in required_headings:
        if h not in doc:
            issues.append(f"缺少章节标题: {h}")

    # 基础长度与证据检查
    if len(doc) < 800:
        issues.append("正文过短，信息密度不足（建议补充更多证据片段后重写）")

    # 统计“参考来源”章节的引用数量
    refs_count = 0
    if "## 参考来源" in doc:
        tail = doc.split("## 参考来源", 1)[1]
        for line in tail.splitlines():
            s = line.strip()
            if s.startswith("- [") and "]" in s:
                refs_count += 1
    if refs_count < 3:
        issues.append(f"参考来源不足（当前 {refs_count} 条，建议 >= 3 条）")

    status = "pass" if not issues else "fail"
    feedback = "；".join(issues) if issues else "结构与引用完整，可进入最终输出。"
    return {
        "review": {
            "status": status,
            "issues": issues,
            "refs": refs_count,
            "iteration": state.get("iteration", 0),
        },
        "review_feedback": feedback,
    }


def _replan_node(state: ResearchState) -> dict:
    """根据审阅反馈重新规划子问题（迭代回路）。"""
    ctx = state["ctx"]
    feedback = (state.get("review_feedback") or "").strip()
    if not feedback:
        feedback = "补充更多可引用的公开资料来源，并完善章节结构与引用。"

    # 保持相同 trace_id，让向量库数据留在同一次运行目录下
    augmented_ctx = MCPContext(
        request=f"{ctx.request}\n\n补充检索重点（来自审阅反馈）：{feedback}",
        created_at=ctx.created_at,
        trace_id=ctx.trace_id,
    )
    subqueries = plan(augmented_ctx)
    return {
        "subqueries": subqueries,
        "expected_subtasks": len(subqueries),
        "iteration": state.get("iteration", 0) + 1,
        "run_id": state.get("run_id", 0) + 1,
    }


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


# ---------- 子任务节点（通过 Send 并行执行） ----------


def _subtask_node(state: dict) -> dict:
    """单个子问题的独立检索 + 索引 + 召回。

    从 Send 负载读取 ``ctx``、``subquery``、``subquery_idx``。
    返回 ``chunks``（由 reducer 追加）与 ``subtask_progress``。
    """
    ctx: MCPContext = state["ctx"]
    subquery: str = state["subquery"]
    idx: int = state["subquery_idx"]
    run_id: int = int(state.get("run_id", 0))
    subdir = f"sub_{idx}"

    docs = search(ctx, query=subquery, max_results=8)
    if not docs:
        return {
            "chunks": [],
            "subtask_progress": [
                {
                    "run_id": run_id,
                    "idx": idx,
                    "subquery": subquery,
                    "docs": 0,
                    "chunks": 0,
                }
            ],
        }

    info = index_documents(ctx, docs, subdir=subdir)
    chunks = retrieve(ctx, query=subquery, subdir=subdir, k_recall=10, k_final=4)

    for c in chunks:
        c["subquery"] = subquery
        c["subquery_idx"] = idx

    return {
        "chunks": chunks,
        "subtask_progress": [
            {
                "run_id": run_id,
                "idx": idx,
                "subquery": subquery,
                "docs": len(docs),
                "indexed_chunks": info.get("chunks", 0),
                "chunks": len(chunks),
            }
        ],
    }


# ---------- 路由 ----------


def _route_from_router(state: ResearchState) -> str:
    return "chat" if state.get("intent") == "chat" else "planner"


def _fan_out_subtasks(state: ResearchState):
    subqueries = state.get("subqueries") or []
    run_id = int(state.get("run_id", 0))
    return [
        Send(
            "subtask",
            {"ctx": state["ctx"], "subquery": q, "subquery_idx": i, "run_id": run_id},
        )
        for i, q in enumerate(subqueries)
    ]


def _join_node(state: ResearchState) -> dict:
    """并行子任务后的汇聚节点。

    该节点会在每个子任务完成时触发，但只有本轮最后一个完成的子任务
    才会触发下游写作。
    """
    return {}


def _route_from_join(state: ResearchState) -> str:
    run_id = int(state.get("run_id", 0))
    expected = int(state.get("expected_subtasks", 0))
    if expected <= 0:
        return "write"

    progress = state.get("subtask_progress") or []
    done_idxs = {
        int(p.get("idx"))
        for p in progress
        if int(p.get("run_id", -1)) == run_id and p.get("idx") is not None
    }
    return "write" if len(done_idxs) >= expected else END


def _route_after_write(state: ResearchState) -> str:
    if state.get("intent") == "email" and state.get("email_to"):
        return "email"
    return END


def _route_after_review(state: ResearchState) -> str:
    review = state.get("review") or {}
    status = str(review.get("status", "fail")).lower()
    if status == "pass":
        return _route_after_write(state)

    # 失败则迭代，直到达到 max_iterations
    iteration = int(state.get("iteration", 0))
    max_iterations = int(state.get("max_iterations", 2))
    if iteration >= max_iterations:
        return _route_after_write(state)
    return "replan"


# ---------- graph ----------


def build_workflow() -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("router", _router_node)
    graph.add_node("chat", _chat_node)
    graph.add_node("planner", _planner_node)
    graph.add_node("orchestrator", _orchestrator_node)
    graph.add_node("subtask", _subtask_node)
    graph.add_node("join", _join_node)
    graph.add_node("write", _write_node)
    graph.add_node("reviewer", _reviewer_node)
    graph.add_node("replan", _replan_node)
    graph.add_node("email", _email_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router", _route_from_router, {"chat": "chat", "planner": "planner"}
    )
    graph.add_edge("chat", END)

    # planner -> orchestrator（显式控制点）
    graph.add_edge("planner", "orchestrator")

    # orchestrator 分叉为 N 个并行子任务
    graph.add_conditional_edges("orchestrator", _fan_out_subtasks, ["subtask"])
    graph.add_edge("subtask", "join")

    # join 会在每个子任务完成时执行；只有最后一个完成会触发写作
    graph.add_conditional_edges("join", _route_from_join, {"write": "write", END: END})

    # write -> reviewer ->（pass/email/end）或（fail -> replan -> orchestrator）
    graph.add_edge("write", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        _route_after_review,
        {"replan": "replan", "email": "email", END: END},
    )
    graph.add_edge("replan", "orchestrator")

    graph.add_edge("email", END)
    return graph.compile()


def build_execution_workflow() -> StateGraph:
    """执行专用工作流：跳过 router 与 planner。

    入口直接落到 orchestrator（research/email）或 chat，
    由调用方通过初始 state 提供 ``intent`` 与 ``subqueries``。
    """
    graph = StateGraph(ResearchState)
    graph.add_node("entry", lambda s: {})
    graph.add_node("chat", _chat_node)
    graph.add_node("orchestrator", _orchestrator_node)
    graph.add_node("subtask", _subtask_node)
    graph.add_node("join", _join_node)
    graph.add_node("write", _write_node)
    graph.add_node("reviewer", _reviewer_node)
    graph.add_node("replan", _replan_node)
    graph.add_node("email", _email_node)

    def _route_from_entry(state: ResearchState) -> str:
        return "chat" if state.get("intent") == "chat" else "orchestrator"

    graph.add_edge(START, "entry")
    graph.add_conditional_edges(
        "entry", _route_from_entry, {"chat": "chat", "orchestrator": "orchestrator"}
    )
    graph.add_edge("chat", END)

    graph.add_conditional_edges("orchestrator", _fan_out_subtasks, ["subtask"])
    graph.add_edge("subtask", "join")
    graph.add_conditional_edges("join", _route_from_join, {"write": "write", END: END})

    graph.add_edge("write", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        _route_after_review,
        {"replan": "replan", "email": "email", END: END},
    )
    graph.add_edge("replan", "orchestrator")

    graph.add_edge("email", END)
    return graph.compile()
