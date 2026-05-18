from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class MCPContext:
    request: str
    created_at: str
    trace_id: str

    @classmethod
    def new(cls, request: str) -> "MCPContext":
        created_at = datetime.utcnow().isoformat() + "Z"
        trace_id = f"trace_{int(datetime.utcnow().timestamp())}"
        return cls(request=request, created_at=created_at, trace_id=trace_id)
