from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

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


def _sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@app.get("/api/research/stream")
async def stream_research(topic: str = Query(..., description="研究主题")):
    async def event_generator():
        ctx = MCPContext.new(topic)
        graph = build_workflow()

        yield _sse("status", {"phase": "searching", "message": f"正在搜索: {topic}"})

        async for mode, chunk in graph.astream(
            {"ctx": ctx, "docs": [], "document": ""},
            stream_mode=["updates", "messages"],
        ):
            if mode == "updates":
                for node_name, node_output in chunk.items():
                    if node_name == "search":
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

            elif mode == "messages":
                msg_chunk, metadata = chunk
                if isinstance(msg_chunk, AIMessageChunk) and msg_chunk.content:
                    yield _sse("token", {"content": msg_chunk.content})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


_WEB_DIR = Path(__file__).parent.parent / "web"
if _WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")
