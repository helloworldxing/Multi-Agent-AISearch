from __future__ import annotations

import json
import os
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.mcp.context import MCPContext
from app.prompts import ROUTER_SYSTEM

_VALID_INTENTS = {"chat", "research", "email"}


def classify(ctx: MCPContext) -> str:
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
        temperature=0,
    )
    response = llm.invoke(
        [
            SystemMessage(content=ROUTER_SYSTEM),
            HumanMessage(content=ctx.request),
        ]
    )
    return _parse_intent(response.content)


def _parse_intent(raw: str) -> str:
    match = re.search(r"\{[^{}]*\}", raw or "")
    if not match:
        return "chat"
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return "chat"
    intent = str(data.get("intent", "")).strip().lower()
    return intent if intent in _VALID_INTENTS else "chat"
