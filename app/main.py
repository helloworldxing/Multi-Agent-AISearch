from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessageChunk

from app.graph.workflow import build_workflow
from app.mcp.context import MCPContext

load_dotenv()

_OUTPUT_DIR = Path(__file__).parent.parent / "data"


async def run_stream(topic: str) -> None:
    ctx = MCPContext.new(topic)
    graph = build_workflow()

    print(f"\033[33m[搜索中]\033[0m 主题: {topic}")

    document = ""

    async for mode, chunk in graph.astream(
        {"ctx": ctx, "docs": [], "document": ""},
        stream_mode=["updates", "messages"],
    ):
        if mode == "updates":
            for node_name, node_output in chunk.items():
                if node_name == "search":
                    docs = node_output.get("docs", [])
                    print(f"\033[32m[已获取]\033[0m {len(docs)} 篇文章")
                    for i, d in enumerate(docs, 1):
                        print(f"  {i}. {d['title']}")
                    print(f"\n\033[34m[撰写中]\033[0m 正在生成文章...\n")
                elif node_name == "write":
                    document = node_output.get("document", "")
        elif mode == "messages":
            msg_chunk, metadata = chunk
            if isinstance(msg_chunk, AIMessageChunk) and msg_chunk.content:
                print(msg_chunk.content, end="", flush=True)

    print("\n")
    _OUTPUT_DIR.mkdir(exist_ok=True)
    filename = _OUTPUT_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filename.write_text(document, encoding="utf-8")
    print(f"\033[32m[完成]\033[0m 已保存至: {filename}")


def main():
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("请输入研究主题: ").strip()
    if not topic:
        print("错误: 请提供研究主题")
        sys.exit(1)
    asyncio.run(run_stream(topic))


if __name__ == "__main__":
    main()
