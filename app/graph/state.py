from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from app.mcp.context import MCPContext


class ResearchState(TypedDict, total=False):
    ctx: MCPContext
    intent: str
    subqueries: list[str]
    # Iteration and control params
    run_id: int
    expected_subtasks: int
    iteration: int
    max_iterations: int
    review: dict
    review_feedback: str
    # Parallel subtasks append via reducer
    chunks: Annotated[list[dict], operator.add]
    subtask_progress: Annotated[list[dict], operator.add]
    document: str
    chat_response: str
    email_to: str
    email_sent: dict
    error: str
