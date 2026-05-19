from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessageChunk

from app.graph.workflow import build_workflow
from app.mcp.context import MCPContext

load_dotenv()

app = FastAPI(title="Multi-Agent Research Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_OUTPUT_DIR = Path(__file__).parent.parent / "data"

# Only stream tokens from these nodes to the user; suppress the router's LLM tokens.
_STREAMABLE_NODES = {"write", "chat"}


def _sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@app.get("/api/research/stream")
async def stream_research(
    topic: str = Query(..., description="用户输入"),
    email: Optional[str] = Query(None, description="收件邮箱（仅 email 意图时使用）"),
):
    async def event_generator():
        ctx = MCPContext.new(topic)
        graph = build_workflow()

        yield _sse("status", {"phase": "routing", "message": "正在判断意图..."})

        initial_state = {
            "ctx": ctx,
            "intent": "",
            "docs": [],
            "document": "",
            "chat_response": "",
            "email_to": (email or "").strip(),
            "email_sent": {},
        }

        async for mode, chunk in graph.astream(
            initial_state,
            stream_mode=["updates", "messages"],
        ):
            if mode == "updates":
                for node_name, node_output in chunk.items():
                    if node_name == "router":
                        intent = node_output.get("intent", "chat")
                        yield _sse("intent", {"intent": intent})
                        if intent == "chat":
                            yield _sse("status", {"phase": "chatting", "message": "正在回答..."})
                        else:
                            yield _sse("status", {"phase": "searching", "message": f"正在搜索: {topic}"})

                    elif node_name == "search":
                        docs = node_output.get("docs", [])
                        yield _sse("search_results", {"count": len(docs), "docs": docs})
                        yield _sse("status", {"phase": "writing", "message": "正在撰写文章..."})

                    elif node_name == "write":
                        document = node_output.get("document", "")
                        _OUTPUT_DIR.mkdir(exist_ok=True)
                        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                        filepath = _OUTPUT_DIR / filename
                        filepath.write_text(document, encoding="utf-8")
                        yield _sse("done", {"file": str(filepath), "message": "撰写完成"})

                    elif node_name == "chat":
                        yield _sse("done", {"message": "回复完成"})

                    elif node_name == "email":
                        if node_output.get("error"):
                            yield _sse("error", {"message": node_output["error"]})
                        else:
                            sent = node_output.get("email_sent", {})
                            yield _sse(
                                "email_sent",
                                {"to": sent.get("to", ""), "message": f"已发送至 {sent.get('to', '')}"},
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


_WEB_DIR = Path(__file__).parent.parent / "web"
if _WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")
