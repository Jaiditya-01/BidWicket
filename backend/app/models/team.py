from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field


class Team(Document):
    name: str
    short_name: Optional[str] = None  # e.g., "CSK"
    owner_id: str  # User id
    tournament_id: Optional[str] = None
    budget: float = 10_000_000.0  # 1 crore default
    remaining_budget: float = 10_000_000.0
    logo_url: Optional[str] = None
    home_ground: Optional[str] = None
    players: list[str] = []  # list of Player ids
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "teams"
