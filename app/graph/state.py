from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from app.mcp.context import MCPContext


class ResearchState(TypedDict, total=False):
    ctx: MCPContext  # 运行上下文
    intent: str  # 意图描述
    subqueries: list[str]  # 子查询列表
    # 迭代/控制
    run_id: int  # 运行ID
    expected_subtasks: int  # 预计子任务数
    iteration: int  # 当前迭代
    max_iterations: int  # 最大迭代
    review: dict  # 评审数据
    review_feedback: str  # 评审反馈
    # 并行子任务合并（使用 operator.add）
    chunks: Annotated[list[dict], operator.add]  # 数据块
    subtask_progress: Annotated[list[dict], operator.add]  # 进度记录
    document: str  # 文档文本
    chat_response: str  # 聊天/LLM 回复
    email_to: str  # 邮件目标
    email_sent: dict  # 邮件状态
    error: str  # 错误摘要
