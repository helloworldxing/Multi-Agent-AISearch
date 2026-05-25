from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessageChunk
from pydantic import BaseModel, Field

from app.agents.planner_agent import plan as planner_plan
from app.agents.router_agent import classify as router_classify
from app.auth import (
    create_token,
    hash_password,
    require_user,
    user_from_query_token,
    verify_password,
)
from app.db import get_conn, init_db
from app.graph.workflow import build_execution_workflow, build_workflow
from app.mcp.context import MCPContext

load_dotenv()
init_db()

app = FastAPI(title="Multi-Agent Research Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_DATA_DIR = Path(__file__).parent.parent / "data"
_OUTPUT_DIR = _DATA_DIR

# 仅将这些节点的 token 流式输出给用户；屏蔽 router / planner / reranker 的 LLM token，
# 避免污染可见输出。
_STREAMABLE_NODES = {"write", "chat"}


def _sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


# ---------- 鉴权与用户面板 ----------


class RegisterPayload(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=128)
    email: Optional[str] = None


class LoginPayload(BaseModel):
    username: str
    password: str


class ProfilePayload(BaseModel):
    email: Optional[str] = None


def _user_dict(row: sqlite3.Row | dict) -> dict:
    d = dict(row)
    return {
        "id": d["id"],
        "username": d["username"],
        "email": d.get("email") or "",
        "created_at": d.get("created_at") or "",
    }


@app.post("/api/auth/register")
def register(payload: RegisterPayload):
    pw_hash = hash_password(payload.password)
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (payload.username, (payload.email or None), pw_hash),
            )
            user_id = cur.lastrowid
            conn.commit()
            row = conn.execute(
                "SELECT id, username, email, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="用户名已被占用"
        )
    user = _user_dict(row)
    return {"token": create_token(user["id"], user["username"]), "user": user}


@app.post("/api/auth/login")
def login(payload: LoginPayload):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, email, password_hash, created_at FROM users WHERE username = ?",
            (payload.username,),
        ).fetchone()
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )
    user = _user_dict(row)
    return {"token": create_token(user["id"], user["username"]), "user": user}


@app.get("/api/auth/me")
def me(user: dict = Depends(require_user)):
    return {"user": _user_dict(user)}


@app.patch("/api/auth/profile")
def update_profile(payload: ProfilePayload, user: dict = Depends(require_user)):
    new_email = (payload.email or "").strip() or None
    with get_conn() as conn:
        conn.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, user["id"]))
        conn.commit()
        row = conn.execute(
            "SELECT id, username, email, created_at FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()
    return {"user": _user_dict(row)}


# ---------- 历史记录 ----------


@app.get("/api/history")
def list_history(user: dict = Depends(require_user)):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, topic, intent, subqueries, file_path, email_to, created_at
            FROM histories WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 200
            """,
            (user["id"],),
        ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        try:
            d["subqueries"] = json.loads(d.get("subqueries") or "[]")
        except json.JSONDecodeError:
            d["subqueries"] = []
        items.append(d)
    return {"items": items}


@app.get("/api/history/{history_id}")
def get_history(history_id: int, user: dict = Depends(require_user)):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, topic, intent, subqueries, document, file_path, email_to, created_at
            FROM histories WHERE id = ? AND user_id = ?
            """,
            (history_id, user["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="未找到该记录")
    d = dict(row)
    try:
        d["subqueries"] = json.loads(d.get("subqueries") or "[]")
    except json.JSONDecodeError:
        d["subqueries"] = []
    return d


@app.delete("/api/history/{history_id}")
def delete_history(history_id: int, user: dict = Depends(require_user)):
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM histories WHERE id = ? AND user_id = ?",
            (history_id, user["id"]),
        )
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="未找到该记录")
    return {"ok": True}


def _save_history(
    *,
    user_id: int,
    topic: str,
    intent: str,
    subqueries: list[str],
    document: str,
    file_path: Optional[str],
    email_to: Optional[str],
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO histories
                (user_id, topic, intent, subqueries, document, file_path, email_to)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                topic,
                intent,
                json.dumps(subqueries or [], ensure_ascii=False),
                document or "",
                file_path or "",
                (email_to or "").strip() or None,
            ),
        )
        conn.commit()
        return cur.lastrowid


# ---------- 研究：plan + stream ----------


@app.get("/api/research/plan")
async def plan_research(
    topic: str = Query(..., description="用户输入"),
    email: Optional[str] = Query(None, description="收件邮箱（仅 email 意图时使用）"),
    _user: dict = Depends(require_user),
):
    """先判断意图并给出执行步骤，由前端展示给用户确认。

    - chat：直接返回意图，不生成步骤（前端会跳过确认面板）。
    - research / email：返回 LLM 拆解的子问题，供用户增删改后再触发 stream 执行。
    """
    ctx = MCPContext.new(topic)
    intent = router_classify(ctx)
    if intent == "email" and not (email or "").strip():
        intent = "research"

    if intent == "chat":
        return {"intent": intent, "subqueries": []}

    subqueries = planner_plan(ctx)
    return {"intent": intent, "subqueries": subqueries}


@app.get("/api/research/stream")
async def stream_research(
    topic: str = Query(..., description="用户输入"),
    email: Optional[str] = Query(None, description="收件邮箱（仅 email 意图时使用）"),
    intent: Optional[str] = Query(
        None,
        description="若提供，则跳过路由直接按该意图执行（chat/research/email）",
    ),
    subqueries: Optional[str] = Query(
        None,
        description="若提供（JSON 数组字符串），则跳过 planner 直接按这些子问题并行执行",
    ),
    token: Optional[str] = Query(
        None,
        description="JWT token（EventSource 不支持自定义请求头，必须以查询参数传入）",
    ),
):
    user = user_from_query_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或令牌已过期")

    preset_intent = (intent or "").strip().lower() or None
    preset_subqueries: Optional[list[str]] = None
    if subqueries:
        try:
            parsed = json.loads(subqueries)
            if isinstance(parsed, list):
                preset_subqueries = [str(q).strip() for q in parsed if str(q).strip()]
        except json.JSONDecodeError:
            preset_subqueries = None

    use_execution_workflow = bool(preset_intent) and (
        preset_intent == "chat" or bool(preset_subqueries)
    )

    async def event_generator():
        ctx = MCPContext.new(topic)

        if use_execution_workflow:
            graph = build_execution_workflow()
            yield _sse(
                "intent",
                {"intent": preset_intent, "skipped_planning": True},
            )
            if preset_intent == "chat":
                yield _sse(
                    "status",
                    {"phase": "chatting", "message": "正在回答..."},
                )
            else:
                yield _sse(
                    "status",
                    {
                        "phase": "researching",
                        "message": f"已确认 {len(preset_subqueries or [])} 个子任务，并行检索中...",
                    },
                )
        else:
            graph = build_workflow()
            yield _sse("status", {"phase": "routing", "message": "正在判断意图..."})

        initial_state = {
            "ctx": ctx,
            "intent": preset_intent or "",
            "subqueries": preset_subqueries or [],
            "expected_subtasks": len(preset_subqueries or []),
            "chunks": [],
            "subtask_progress": [],
            "document": "",
            "chat_response": "",
            "email_to": (email or "").strip(),
            "email_sent": {},
        }

        total_subtasks = len(preset_subqueries or []) if use_execution_workflow else 0
        finished_subtasks = 0

        # 累积态用于落库
        final_intent = preset_intent or ""
        final_subqueries: list[str] = list(preset_subqueries or [])
        final_document = ""
        final_filepath: Optional[str] = None
        final_chat = ""

        async for mode, chunk in graph.astream(
            initial_state,
            stream_mode=["updates", "messages"],
        ):
            if mode == "updates":
                for node_name, node_output in chunk.items():
                    # 全局节点错误事件：若节点返回 error 字段，则立即将错误通过 SSE 发送给前端
                    if isinstance(node_output, dict) and node_output.get("error"):
                        yield _sse(
                            "error",
                            {"node": node_name, "message": node_output["error"]},
                        )
                    if node_name == "router":
                        intent_val = node_output.get("intent", "chat")
                        final_intent = intent_val
                        yield _sse("intent", {"intent": intent_val})
                        if intent_val == "chat":
                            yield _sse(
                                "status",
                                {"phase": "chatting", "message": "正在回答..."},
                            )
                        else:
                            yield _sse(
                                "status",
                                {"phase": "planning", "message": "正在拆解研究任务..."},
                            )

                    elif node_name == "planner":
                        subqueries_val = node_output.get("subqueries", []) or []
                        final_subqueries = list(subqueries_val)
                        total_subtasks = len(subqueries_val)
                        finished_subtasks = 0
                        yield _sse(
                            "plan_done",
                            {
                                "count": total_subtasks,
                                "subqueries": subqueries_val,
                            },
                        )
                        yield _sse(
                            "status",
                            {
                                "phase": "researching",
                                "message": f"已拆解为 {total_subtasks} 个子任务，并行检索中...",
                            },
                        )

                    elif node_name == "subtask":
                        progress_list = node_output.get("subtask_progress", []) or []
                        for p in progress_list:
                            # 如果子任务被标记为失败，额外发出 error 事件
                            if p.get("status") == "failed":
                                yield _sse(
                                    "error",
                                    {
                                        "node": "subtask",
                                        "idx": p.get("idx"),
                                        "message": p.get("result") or "子任务失败",
                                    },
                                )
                            finished_subtasks += 1
                            yield _sse(
                                "subtask_done",
                                {
                                    "idx": p.get("idx"),
                                    "subquery": p.get("subquery", ""),
                                    "docs": p.get("docs", 0),
                                    "indexed_chunks": p.get("indexed_chunks", 0),
                                    "chunks": p.get("chunks", 0),
                                    "finished": finished_subtasks,
                                    "total": total_subtasks,
                                },
                            )
                        if total_subtasks and finished_subtasks >= total_subtasks:
                            yield _sse(
                                "status",
                                {
                                    "phase": "writing",
                                    "message": "所有子任务完成，正在汇总撰写...",
                                },
                            )

                    elif node_name == "write":
                        document = node_output.get("document", "")
                        final_document = document
                        _OUTPUT_DIR.mkdir(exist_ok=True)
                        filename = (
                            f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                        )
                        filepath = _OUTPUT_DIR / filename
                        filepath.write_text(document, encoding="utf-8")
                        final_filepath = str(filepath)
                        history_id = _save_history(
                            user_id=user["id"],
                            topic=topic,
                            intent=final_intent or "research",
                            subqueries=final_subqueries,
                            document=document,
                            file_path=final_filepath,
                            email_to=email,
                        )
                        yield _sse(
                            "done",
                            {
                                "file": final_filepath,
                                "message": "撰写完成",
                                "history_id": history_id,
                            },
                        )

                    elif node_name == "chat":
                        final_chat = node_output.get("chat_response", "")
                        history_id = _save_history(
                            user_id=user["id"],
                            topic=topic,
                            intent="chat",
                            subqueries=[],
                            document=final_chat,
                            file_path=None,
                            email_to=None,
                        )
                        yield _sse(
                            "done",
                            {"message": "回复完成", "history_id": history_id},
                        )

                    elif node_name == "email":
                        if node_output.get("error"):
                            yield _sse("error", {"message": node_output["error"]})
                        else:
                            sent = node_output.get("email_sent", {})
                            yield _sse(
                                "email_sent",
                                {
                                    "to": sent.get("to", ""),
                                    "message": f"已发送至 {sent.get('to', '')}",
                                },
                            )

            elif mode == "messages":
                msg_chunk, metadata = chunk
                node = (metadata or {}).get("langgraph_node", "")
                if (
                    isinstance(msg_chunk, AIMessageChunk)
                    and msg_chunk.content
                    and node in _STREAMABLE_NODES
                ):
                    yield _sse("token", {"content": msg_chunk.content})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------- 静态资源（生产合并部署） ----------

_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
_LEGACY_WEB = Path(__file__).parent.parent / "web"


class SPAStaticFiles(StaticFiles):
    """静态资源 + SPA 兜底：未知路径返回 index.html，让前端 router 处理。"""

    async def get_response(self, path: str, scope):  # type: ignore[override]
        try:
            return await super().get_response(path, scope)
        except Exception:
            # 任何 404 都回落到 index.html，由前端 React Router 决定路由
            return await super().get_response("index.html", scope)


if _FRONTEND_DIST.exists():
    app.mount("/", SPAStaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")
elif _LEGACY_WEB.exists():
    app.mount("/", StaticFiles(directory=_LEGACY_WEB, html=True), name="legacy-web")
