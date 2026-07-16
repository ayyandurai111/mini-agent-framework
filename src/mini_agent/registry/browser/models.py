from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Any, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclasses.dataclass
class ToolResponse:
    success: bool
    tool: str
    message: str
    data: Any = dataclasses.field(default_factory=dict)
    error: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: str = dataclasses.field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @staticmethod
    def ok(tool: str, message: str, data: Any = None) -> "ToolResponse":
        return ToolResponse(success=True, tool=tool, message=message, data=data or {})

    @staticmethod
    def fail(
        tool: str,
        message: str,
        error: str,
        error_code: str = "error",
        data: Any = None,
    ) -> "ToolResponse":
        return ToolResponse(
            success=False,
            tool=tool,
            message=message,
            data=data or {},
            error=error,
            error_code=error_code,
        )
