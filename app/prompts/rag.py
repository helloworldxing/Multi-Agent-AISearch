"""Prompts for retrieval reranking."""
from __future__ import annotations

RERANK_SYSTEM = """你是一名严格的相关性评判员。我会给你一个"用户查询"和若干编号候选片段，请按"片段对回答该查询的有用程度"从高到低排序。

判断维度：
- 片段是否直接回答了查询的核心信息需求
- 片段是否提供了具体数据、事实、案例或结论（优于纯背景介绍）
- 片段内容是否与查询主题强相关，而非泛化或离题

只输出一个严格 JSON，不要任何解释、不要 Markdown 代码块：
{"ranking": [<最相关编号>, <次相关编号>, ...]}

规则：
- ranking 数组的元素是候选片段的编号（整数）。
- 必须只包含传入的候选编号，不得新增、不得重复。
- 完全不相关的片段可以省略不写。
"""


def build_rerank_user_message(query: str, chunks: list[dict]) -> str:
    blocks = []
    for c in chunks:
        text = (c.get("text") or "").strip().replace("\n", " ")
        if len(text) > 600:
            text = text[:600] + "..."
        blocks.append(f"[{c['id']}] 来源: {c.get('title', '')}\n     内容: {text}")
    body = "\n\n".join(blocks)
    return f"用户查询: {query}\n\n候选片段:\n{body}"
