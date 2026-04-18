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


class MatchStage(str, Enum):
    league = "league"
    quarter_final = "quarter_final"
    semi_final = "semi_final"
    final = "final"


class BatterScore(BaseModel):
    player_id: str
    runs: int = 0
    balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    is_out: bool = False


class BowlerScore(BaseModel):
    player_id: str
    overs: float = 0.0
    runs_conceded: int = 0
    wickets: int = 0
    maidens: int = 0


class InningsScore(BaseModel):
    team_id: Optional[str] = None  # Legacy field
    batting_team_id: Optional[str] = None
    bowling_team_id: Optional[str] = None
    runs: int = 0
    wickets: int = 0
    overs: float = 0.0
    extras: int = 0
    batters: List[BatterScore] = []
    bowlers: List[BowlerScore] = []


class Commentary(BaseModel):
    over: float
    ball_description: str
    runs_scored: int = 0
    wicket: bool = False
    batter_id: Optional[str] = None
    bowler_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Match(Document):
    tournament_id: str
    team1_id: str
    team2_id: str
    venue: Optional[str] = None
    match_date: Optional[datetime] = None
    stage: MatchStage = MatchStage.league
    status: MatchStatus = MatchStatus.scheduled
    toss_winner_id: Optional[str] = None
    toss_decision: Optional[str] = None  # "bat" | "bowl"
    current_innings: int = 1
    innings1: Optional[InningsScore] = None
    innings2: Optional[InningsScore] = None
    winner_id: Optional[str] = None
    result_description: Optional[str] = None
    highlights_url: Optional[str] = None
    commentary: List[Commentary] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "matches"
