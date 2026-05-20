from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.mcp.context import MCPContext
from app.prompts import WRITER_SYSTEM, build_writer_user_message


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
        temperature=0.7,
        streaming=True,
    )


def write(ctx: MCPContext, chunks: list[dict]) -> str:
    """基于重排后的 RAG 片段生成研究报告。

    ``chunks`` 来自 ``rag_agent.retrieve``，按相关性排序，格式为
    ``{"id", "title", "url", "text", "doc_index"}``。
    """
    user_message = build_writer_user_message(ctx.request, chunks)
    llm = _build_llm()
    response = llm.invoke(
        [
            SystemMessage(content=WRITER_SYSTEM),
            HumanMessage(content=user_message),
        ]
    )
    return response.content
