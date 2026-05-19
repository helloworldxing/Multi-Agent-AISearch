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
    """Generate the research report from reranked RAG chunks.

    ``chunks`` is the output of ``rag_agent.retrieve`` — a list of
    ``{"id", "title", "url", "text", "doc_index"}`` ordered by relevance.
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
