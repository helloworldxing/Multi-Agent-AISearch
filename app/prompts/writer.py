"""Prompts for the writer agent.

Provides:
- WRITER_SYSTEM: high-quality research-writing system prompt
- build_writer_user_message: formats reranked RAG chunks into the user turn
"""
from __future__ import annotations

WRITER_SYSTEM = """你是一名资深的中文研究员与撰稿人。基于"用户主题"和经过精排的"证据片段"，输出一篇结构清晰、逻辑严密、可直接发布的 Markdown 研究报告。

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
3. "关键发现"用 3-6 条要点列出可验证的结论，每条末尾用 `[n]` 引用对应来源编号（n 为下方"证据片段"的来源编号）。
4. "详细分析"分若干小节（### 子标题），综合多源信息，避免照抄原文段落。所有事实性陈述都用 `[n]` 标注来源；同一句话引用多源用 `[1][3]`。
5. "结论与展望"给出可操作的洞察 / 趋势判断，不要泛泛而谈。
6. "参考来源"按编号列出：`- [n] 标题 — URL`。每个被正文引用过的来源都必须出现在此处。
7. 严禁捏造事实、链接或数据。证据片段中没有的内容不得写入正文。如果片段之间冲突，明确指出"来源 [a] 与 [b] 存在分歧"。
8. 如果证据片段不足以支撑某一节，写"现有资料不足以充分回答此问题"，不要凑字数。
9. 不要输出任何 Markdown 代码块包裹整篇文章；正文中允许使用代码块举例。
"""


def build_writer_user_message(topic: str, chunks: list[dict]) -> str:
    """Format the reranked RAG chunks into the user turn.

    Each chunk is expected to have ``title``, ``url``, ``text`` and
    ``doc_index``. Chunks from the same source document share a single
    citation number, so the writer can cite ``[n]`` consistently regardless
    of how many chunks from that source were retained.
    """
    if not chunks:
        return f"研究主题：{topic}\n\n（未检索到相关证据，请如实说明资料不足。）"

    doc_index_to_citation: dict[int, int] = {}
    citations: list[dict] = []
    for c in chunks:
        di = c.get("doc_index", -1)
        if di not in doc_index_to_citation:
            doc_index_to_citation[di] = len(citations) + 1
            citations.append({
                "n": doc_index_to_citation[di],
                "title": c.get("title", ""),
                "url": c.get("url", ""),
            })

    chunk_blocks = []
    for c in chunks:
        n = doc_index_to_citation[c.get("doc_index", -1)]
        text = (c.get("text") or "").strip()
        chunk_blocks.append(
            f"[{n}] 来源标题: {c.get('title', '')}\n"
            f"     URL: {c.get('url', '')}\n"
            f"     片段内容: {text}"
        )

    sources_block = "\n\n".join(chunk_blocks)
    citation_block = "\n".join(
        f"[{c['n']}] {c['title']} — {c['url']}" for c in citations
    )

    return (
        f"研究主题：{topic}\n\n"
        f"以下是经过精排的证据片段（同一来源的多条片段共用同一编号）：\n\n"
        f"{sources_block}\n\n"
        f"来源编号映射（用于正文 [n] 引用与参考来源章节）：\n{citation_block}"
    )
