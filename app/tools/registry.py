from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

from app.agents.search_agent import search
from app.agents.writer_agent import write
from app.mcp.context import MCPContext


ToolFn = Callable[..., object]


@dataclass
class ToolRegistry:
    tools: Dict[str, ToolFn]

    @classmethod
    def default(cls) -> "ToolRegistry":
        return cls(tools={
            "search": search,
            "summarize": write,
        })

    def get(self, name: str) -> ToolFn:
        return self.tools[name]
