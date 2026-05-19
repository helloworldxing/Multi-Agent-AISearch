"""Centralized prompt module.

All agent prompts live here so they can be reviewed, version-controlled,
and tuned without touching agent control flow.
"""
from app.prompts.router import ROUTER_SYSTEM
from app.prompts.chat import CHAT_SYSTEM
from app.prompts.writer import WRITER_SYSTEM, build_writer_user_message
from app.prompts.rag import RERANK_SYSTEM, build_rerank_user_message
from app.prompts.planner import PLANNER_SYSTEM

__all__ = [
    "ROUTER_SYSTEM",
    "CHAT_SYSTEM",
    "WRITER_SYSTEM",
    "build_writer_user_message",
    "RERANK_SYSTEM",
    "build_rerank_user_message",
    "PLANNER_SYSTEM",
]
