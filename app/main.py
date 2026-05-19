from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from app.graph.workflow import build_workflow
from app.mcp.context import MCPContext

load_dotenv()

_OUTPUT_DIR = Path(__file__).parent.parent / "data"


def run(topic: str) -> None:
    ctx = MCPContext.new(topic)
    graph = build_workflow()

    print(f"[搜索中] 主题: {topic}")
    result = graph.invoke({"ctx": ctx, "docs": [], "document": ""})

    print(f"[已获取] {len(result['docs'])} 篇文章")

    _OUTPUT_DIR.mkdir(exist_ok=True)
    filename = _OUTPUT_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filename.write_text(result["document"], encoding="utf-8")

    print(f"[完成] 已保存至: {filename}")
    print("\n" + "=" * 60)
    print(result["document"])


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("请输入研究主题: ").strip()
    if not topic:
        print("错误: 请提供研究主题")
        sys.exit(1)
    run(topic)
