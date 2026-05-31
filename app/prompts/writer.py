"""写作智能体提示词。

包含：
- WRITER_SYSTEM：高质量研究写作系统提示词
- build_writer_user_message：将重排后的 RAG 片段（可能来自多个并行子问题）
    格式化为用户输入
"""

from __future__ import annotations

WRITER_SYSTEM = """你是一名资深的中文研究员与撰稿人。基于"用户主题"和经过精排的"证据片段"（可能来自多个并行子任务的检索），输出一篇结构清晰、逻辑严密、可直接发布的 Markdown 研究报告。

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
4. "详细分析"分若干 ### 子标题。可以参考下方"子任务列表"作为分析维度的提示，但最终结构由你判断。每段事实性陈述都要 `[n]` 标注来源；同一句话引用多源用 `[1][3]`。
5. "结论与展望"给出可操作的洞察与趋势判断，不要泛泛而谈。
6. "参考来源"按编号列出：`- [n] 标题 — URL`。每个被正文引用过的来源都必须出现在此处，且仅出现一次（同一来源的多条片段共用同一编号）。
7. 严禁捏造事实、链接或数据。证据片段中没有的内容不得写入正文。如果片段之间冲突，明确指出"来源 [a] 与 [b] 存在分歧"。
8. 如果某一节缺乏证据支撑，写"现有资料不足以充分回答此问题"，不要凑字数。
9. 不要输出任何 Markdown 代码块包裹整篇文章；正文中允许使用代码块举例。
"""


def build_writer_user_message(topic: str, chunks: list[dict]) -> str:
    """为写作智能体格式化片段（可能来自多个并行子任务）。

    引用编号基于 URL：不同子任务但同一来源页面共享一个编号。
    若有 ``subquery``，则暴露给写作端，便于在合适时按规划维度组织“详细分析”。
    """
    if not chunks:
        return f"研究主题：{topic}\n\n（未检索到相关证据，请如实说明资料不足。）"

    # 构建 URL → 引用编号映射（按首次出现顺序稳定编号）
    url_to_citation: dict[str, int] = {}
    citations: list[dict] = []
    for c in chunks:
        url = c.get("url") or f"__no_url_{c.get('subquery_idx', '?')}_{id(c)}"
        if url not in url_to_citation:
            url_to_citation[url] = len(citations) + 1
            citations.append(
                {
                    "n": url_to_citation[url],
                    "title": c.get("title", ""),
                    "url": c.get("url", ""),
                }
            )

    # 汇总子问题列表（去重并保持插入顺序）
    seen_sq: set[str] = set()
    subqueries: list[str] = []
    for c in chunks:
        sq = c.get("subquery", "")
        if sq and sq not in seen_sq:
            seen_sq.add(sq)
            subqueries.append(sq)

    chunk_blocks = []
    for c in chunks:
        url = c.get("url") or f"__no_url_{c.get('subquery_idx', '?')}_{id(c)}"
        n = url_to_citation[url]
        text = (c.get("text") or "").strip()
        sq = c.get("subquery", "")
        sq_line = f"     [对应子任务: {sq}]\n" if sq else ""
        chunk_blocks.append(
            f"[{n}] 来源标题: {c.get('title', '')}\n"
            f"     URL: {c.get('url', '')}\n"
            f"{sq_line}"
            f"     片段内容: {text}"
        )

    sources_block = "\n\n".join(chunk_blocks)
    citation_block = "\n".join(
        f"[{c['n']}] {c['title']} — {c['url']}" for c in citations
    )
    sub_block = (
        "\n".join(f"- {s}" for s in subqueries) if subqueries else "(无显式子任务列表)"
    )

    return (
        f"研究主题：{topic}\n\n"
        f"子任务列表（可作为'详细分析'章节的维度提示）：\n{sub_block}\n\n"
        f"以下是经过精排的证据片段（同一来源的多条片段共用同一编号）：\n\n"
        f"{sources_block}\n\n"
        f"来源编号映射（用于正文 [n] 引用与参考来源章节）：\n{citation_block}"
    )
