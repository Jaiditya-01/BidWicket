from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class EmailVerificationToken(Document):
    user_id: Indexed(str)  # type: ignore[valid-type]
    token_hash: Indexed(str, unique=True)  # type: ignore[valid-type]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    used_at: Optional[datetime] = None

    class Settings:
        name = "email_verification_tokens"


class PasswordResetToken(Document):
    user_id: Indexed(str)  # type: ignore[valid-type]
    token_hash: Indexed(str, unique=True)  # type: ignore[valid-type]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    used_at: Optional[datetime] = None

    class Settings:
        name = "password_reset_tokens"
