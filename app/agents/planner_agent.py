from __future__ import annotations

import json
import os
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.mcp.context import MCPContext
from app.prompts import PLANNER_SYSTEM

_MAX_SUBQUERIES = 6
_MIN_SUBQUERIES = 1


def plan(ctx: MCPContext) -> list[str]:
    """Decompose ctx.request into 3-6 parallel sub-queries.

    Falls back to ``[ctx.request]`` if the LLM output cannot be parsed,
    so the downstream pipeline never sees an empty plan.
    """
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
        temperature=0.3,
    )
    response = llm.invoke(
        [
            SystemMessage(content=PLANNER_SYSTEM),
            HumanMessage(content=ctx.request),
        ]
    )
    subs = _parse_subqueries(response.content)
    if len(subs) < _MIN_SUBQUERIES:
        return [ctx.request]
    return subs[:_MAX_SUBQUERIES]


def _parse_subqueries(raw: str) -> list[str]:
    if not raw:
        return []
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    items = data.get("subqueries") or []
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        s = str(item).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out
