from __future__ import annotations

import json
import os
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.mcp.context import MCPContext

_ROUTER_PROMPT = """你是意图分类器，只输出严格 JSON，不要任何解释或 Markdown 代码块。

将用户输入分类为以下之一：
- chat: 普通对话、问答、闲聊、解释概念、代码问题，不需要联网搜索
- research: 用户希望调研某主题、需要一篇报告/文档/总结/综述
- email: 用户明确要求把研究结果"发送/发到/邮件到/email"某处

输出格式：{"intent": "chat"} 或 {"intent": "research"} 或 {"intent": "email"}"""


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
            SystemMessage(content=_ROUTER_PROMPT),
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
