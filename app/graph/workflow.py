from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.agents.chat_agent import chat
from app.agents.email_agent import send_email
from app.agents.planner_agent import plan
from app.agents.rag_agent import index_documents, retrieve
from app.agents.router_agent import classify
from app.agents.search_agent import search
from app.agents.writer_agent import write
from app.graph.state import ResearchState
from app.mcp.context import MCPContext

# 简单的重试封装，针对 429/500 或临时异常做指数退避重试
import time
from typing import Callable, Any


def rate_limited_call(
    func: Callable[..., Any], *args, retries: int = 3, backoff: float = 0.5, **kwargs
) -> Any:
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            msg = str(e) or ""
            # 简单判断是否为速率限制/临时服务错误
            if (
                any(code in msg for code in ("429", "500", "502", "503", "504"))
                or attempt < retries
            ):
                wait = backoff * (2 ** (attempt - 1))
                time.sleep(wait)
                continue
            raise
    if last_exc:
        raise last_exc


# ---------- 单步节点 ----------


def _router_node(state: ResearchState) -> dict:
    try:
        intent = classify(state["ctx"])
    except Exception:
        # 兜底为 chat，确保流程不被阻塞
        intent = "chat"
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
    try:
        subqueries = plan(state["ctx"])
        # 如果 planner 返回空，兜底为将原始 request 作为单任务
        if not subqueries:
            subqueries = [state["ctx"].request]
    except Exception:
        # 兜底结构化三步计划，避免下游空计划
        req = getattr(state.get("ctx"), "request", "任务")
        subqueries = [
            f"概述：请给出关于“{req}”的高层次概述",
            f"检索：列出需要检索的 3 个关键子问题以支撑报告",
            f"撰写：基于检索结果合成一个包含摘要与结论的草稿",
        ]

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
    try:
        chunks = state.get("chunks", [])
        document = write(state["ctx"], chunks)
        return {"document": document}
    except Exception as e:
        # 生成失败返回占位草稿，流程继续到 reviewer
        return {"document": "生成报告失败。", "error": f"write_failed: {e}"}


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

    try:
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
    except Exception:
        # 解析失败直接兜底为通过，避免阻塞流程
        return {
            "review": {
                "status": "pass",
                "issues": [],
                "refs": refs_count,
                "iteration": state.get("iteration", 0),
            },
            "review_feedback": "解析失败兜底",
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

    # 对检索与索引过程增加兜底与重试
    try:
        docs = rate_limited_call(search, ctx, query=subquery, max_results=8)
    except Exception as e:
        # 单个子任务检索失败，标注为失败并继续其他子任务
        return {
            "chunks": [],
            "subtask_progress": [
                {
                    "run_id": run_id,
                    "idx": idx,
                    "subquery": subquery,
                    "docs": 0,
                    "chunks": 0,
                    "status": "failed",
                    "result": f"检索失败: {e}",
                }
            ],
        }

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
                    "status": "empty",
                }
            ],
        }

    try:
        info = rate_limited_call(index_documents, ctx, docs, subdir=subdir)
        chunks = rate_limited_call(
            retrieve, ctx, query=subquery, subdir=subdir, k_recall=10, k_final=4
        )
    except Exception as e:
        return {
            "chunks": [],
            "subtask_progress": [
                {
                    "run_id": run_id,
                    "idx": idx,
                    "subquery": subquery,
                    "docs": len(docs),
                    "chunks": 0,
                    "status": "failed",
                    "result": f"索引或召回失败: {e}",
                }
            ],
        }

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


# 把一个大任务拆成多个小任务，然后并行发给多个 subtask 节点执行
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


def _verifier_node(state: ResearchState) -> dict:
    """验证正文引用编号等格式；若缺失返回需要重写标记并增加写作修订计数。"""
    doc = (state.get("document") or "").strip()
    refs_count = 0
    if "## 参考来源" in doc:
        tail = doc.split("## 参考来源", 1)[1]
        for line in tail.splitlines():
            s = line.strip()
            if s.startswith("- [") and "]" in s:
                refs_count += 1

    needs_revision = False
    reason = ""
    if refs_count < 3:
        needs_revision = True
        reason = "参考来源不足或引用编号缺失"

    write_revisions = int(state.get("write_revisions", 0))
    if needs_revision:
        write_revisions += 1

    return {
        "verifier": {"needs_revision": needs_revision, "reason": reason},
        "write_revisions": write_revisions,
    }


def _route_from_verifier(state: ResearchState) -> str:
    v = state.get("verifier") or {}
    if v.get("needs_revision"):
        if int(state.get("write_revisions", 0)) >= int(state.get("max_revisions", 2)):
            return "reviewer"
        return "write"
    return "reviewer"


# ---------- graph ----------


# 自动判意图和生成
def build_workflow() -> StateGraph:
    # 构建图
    graph = StateGraph(ResearchState)
    # 添加节点
    graph.add_node("router", _router_node)
    graph.add_node("chat", _chat_node)
    graph.add_node("planner", _planner_node)
    graph.add_node("orchestrator", _orchestrator_node)
    graph.add_node("subtask", _subtask_node)
    graph.add_node("join", _join_node)
    graph.add_node("write", _write_node)
    graph.add_node("verifier", _verifier_node)
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

    # write -> verifier -> reviewer 或 writer(重写)
    graph.add_edge("write", "verifier")
    graph.add_conditional_edges(
        "verifier",
        _route_from_verifier,
        {"write": "write", "reviewer": "reviewer"},
    )

    # reviewer ->（pass/email/end）或（fail -> replan -> orchestrator）
    graph.add_conditional_edges(
        "reviewer",
        _route_after_review,
        {"replan": "replan", "email": "email", END: END},
    )
    graph.add_edge("replan", "orchestrator")

    graph.add_edge("email", END)
    return graph.compile()


# 执行版，跳过 router/planner
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
    graph.add_node("verifier", _verifier_node)
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

    graph.add_edge("write", "verifier")
    graph.add_conditional_edges(
        "verifier",
        _route_from_verifier,
        {"write": "write", "reviewer": "reviewer"},
    )
    graph.add_conditional_edges(
        "reviewer",
        _route_after_review,
        {"replan": "replan", "email": "email", END: END},
    )
    graph.add_edge("replan", "orchestrator")

    graph.add_edge("email", END)
    return graph.compile()
