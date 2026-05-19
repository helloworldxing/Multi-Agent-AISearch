"""Prompts for the writer agent.

Provides:
- WRITER_SYSTEM: high-quality research-writing system prompt
- build_writer_user_message: formats search results into the user turn
"""
from __future__ import annotations

WRITER_SYSTEM = """你是一名资深的中文研究员与撰稿人。基于"用户主题"和若干"搜索结果片段"，输出一篇结构清晰、逻辑严密、可直接发布的 Markdown 研究报告。

写作要求：
1. 仅使用简体中文；语言专业、中性、客观，不使用第一人称。
2. 严格按以下章节顺序组织（用 Markdown 标题）：
   # {主题作为标题}
   ## 摘要
   ## 背景与动机
   ## 关键发现
   ## 详细分析
   ## 结论与展望
   ## 参考来源
3. "关键发现"用 3-6 条要点列出可验证的结论，每条末尾用 `[n]` 引用对应来源编号。
4. "详细分析"分若干小节（### 子标题），综合多源信息，避免照抄原文段落。所有事实性陈述都用 `[n]` 标注来源；同一句话引用多源用 `[1][3]`。
5. "结论与展望"给出可操作的洞察 / 趋势判断，不要泛泛而谈。
6. "参考来源"按编号列出：`- [n] 标题 — URL`。
7. 不要捏造事实、链接或数据；如果搜索结果之间冲突，明确指出"来源 [a] 与 [b] 存在分歧"，不要单方面采信。
8. 如果搜索结果信息不足以支撑某一节，写"现有资料不足以充分回答此问题"，不要凑字数。
9. 不要输出任何 Markdown 代码块包裹整篇文章；正文中允许使用代码块举例。
"""


def build_writer_user_message(topic: str, docs: list[dict]) -> str:
    """Format the user-turn message that pairs with WRITER_SYSTEM."""
    if not docs:
        sources_block = "（无搜索结果）"
    else:
        sources_block = "\n\n".join(
            f"[{i + 1}] 标题: {d.get('title', '')}\n"
            f"    URL: {d.get('url', '')}\n"
            f"    摘要: {(d.get('content') or '')[:600]}"
            for i, d in enumerate(docs)
        )
    return (
        f"研究主题：{topic}\n\n"
        f"以下是检索到的来源，请基于这些来源撰写报告，并在正文中用 [n] 引用对应编号：\n\n"
        f"{sources_block}"
    )
