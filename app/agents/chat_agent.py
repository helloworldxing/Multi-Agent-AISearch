from __future__ import annotations

import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.mcp.context import MCPContext
from app.prompts import CHAT_SYSTEM


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
            SystemMessage(content=CHAT_SYSTEM),
            HumanMessage(content=ctx.request),
        ]
    )
    return response.content
