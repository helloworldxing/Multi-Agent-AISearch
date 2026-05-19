from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.mcp.context import MCPContext

_CHAT_PROMPT = "你是一个友好、专业的中文 AI 助手。直接、清晰地回答用户的问题。"


def chat(ctx: MCPContext) -> str:
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
        temperature=0.7,
        streaming=True,
    )
    response = llm.invoke(
        [
            SystemMessage(content=_CHAT_PROMPT),
            HumanMessage(content=ctx.request),
        ]
    )
    return response.content
