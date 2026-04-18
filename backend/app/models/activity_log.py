from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from beanie import Document, Indexed
from pydantic import Field


class ActivityLog(Document):
    user_id: Indexed(str) | None = None  # type: ignore[valid-type]
    action: str
    success: bool = True

    ip: Optional[str] = None
    user_agent: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "activity_logs"
