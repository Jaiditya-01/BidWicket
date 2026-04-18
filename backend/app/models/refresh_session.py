from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class RefreshSession(Document):
    user_id: Indexed(str)  # type: ignore[valid-type]
    refresh_jti: Indexed(str, unique=True)  # type: ignore[valid-type]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime

    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    replaced_by_jti: Optional[str] = None

    class Settings:
        name = "refresh_sessions"
