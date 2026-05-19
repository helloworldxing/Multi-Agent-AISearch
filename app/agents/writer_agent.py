from __future__ import annotations

import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.mcp.context import MCPContext

_SYSTEM_PROMPT = """你是一名专业的研究员和撰稿人。根据提供的搜索结果，撰写一篇结构清晰、内容详实的 Markdown 文章。

要求：
- 使用中文撰写
- 包含标题、摘要、正文（分小节）、参考来源
- 正文应综合多篇来源的信息，不要逐条复制
- 参考来源部分列出所有来源的标题和链接"""


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
        temperature=0.7,
    )


def write(ctx: MCPContext, docs: list[dict]) -> str:
    sources_block = "\n".join(
        f"[来源 {i+1}] 标题: {d['title']}\nURL: {d['url']}\n内容摘要: {d['content'][:500]}"
        for i, d in enumerate(docs)
    )
    user_message = f"研究主题：{ctx.request}\n\n搜索结果：\n{sources_block}"

    llm = _build_llm()
    response = llm.invoke(
        [
            HumanMessage(content=f"{_SYSTEM_PROMPT}\n\n{user_message}"),
        ]
    )
    return response.content
