from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum

from beanie import Document
from pydantic import BaseModel, Field


class MatchStatus(str, Enum):
    scheduled = "scheduled"
    live = "live"
    completed = "completed"
    abandoned = "abandoned"


class InningsScore(BaseModel):
    team_id: str
    runs: int = 0
    wickets: int = 0
    overs: float = 0.0
    extras: int = 0


class Commentary(BaseModel):
    over: float
    ball_description: str
    runs_scored: int = 0
    wicket: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Match(Document):
    tournament_id: str
    team1_id: str
    team2_id: str
    venue: Optional[str] = None
    match_date: Optional[datetime] = None
    status: MatchStatus = MatchStatus.scheduled
    toss_winner_id: Optional[str] = None
    toss_decision: Optional[str] = None  # "bat" | "bowl"
    innings1: Optional[InningsScore] = None
    innings2: Optional[InningsScore] = None
    winner_id: Optional[str] = None
    result_description: Optional[str] = None
    commentary: List[Commentary] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "matches"
