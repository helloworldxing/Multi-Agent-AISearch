"""集中管理提示词的模块。

所有智能体提示词都集中在此，便于审阅、版本控制，
且无需修改智能体控制流即可调优。
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
