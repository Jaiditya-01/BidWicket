from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.models.match import MatchStage, MatchStatus, InningsScore, Commentary


class MatchCreate(BaseModel):
    tournament_id: str
    team1_id: str
    team2_id: str
    venue: Optional[str] = None
    match_date: Optional[datetime] = None
    stage: MatchStage = MatchStage.league
    highlights_url: Optional[str] = None


class MatchUpdate(BaseModel):
    venue: Optional[str] = None
    match_date: Optional[datetime] = None
    stage: Optional[MatchStage] = None
    status: Optional[MatchStatus] = None
    toss_winner_id: Optional[str] = None
    toss_decision: Optional[str] = None
    current_innings: Optional[int] = None
    innings1: Optional[InningsScore] = None
    innings2: Optional[InningsScore] = None
    winner_id: Optional[str] = None
    result_description: Optional[str] = None
    highlights_url: Optional[str] = None


class CommentaryCreate(BaseModel):
    over: float
    ball_description: str
    runs_scored: int = 0
    wicket: bool = False
    batter_id: Optional[str] = None
    bowler_id: Optional[str] = None


class MatchOut(BaseModel):
    id: str
    tournament_id: str
    team1_id: str
    team2_id: str
    venue: Optional[str]
    match_date: Optional[datetime]
    stage: MatchStage
    status: MatchStatus
    toss_winner_id: Optional[str]
    toss_decision: Optional[str]
    current_innings: int
    innings1: Optional[InningsScore]
    innings2: Optional[InningsScore]
    winner_id: Optional[str]
    result_description: Optional[str]
    highlights_url: Optional[str]
    commentary: List[Commentary]
    created_at: datetime

    class Config:
        from_attributes = True
