from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.tournament import TournamentType, TournamentStatus


class TournamentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    tournament_type: TournamentType = TournamentType.league
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_teams: int = 8
    logo_url: Optional[str] = None


class TournamentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tournament_type: Optional[TournamentType] = None
    status: Optional[TournamentStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_teams: Optional[int] = None
    logo_url: Optional[str] = None


class TournamentOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    tournament_type: TournamentType
    status: TournamentStatus
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    organizer_id: Optional[str]
    max_teams: int
    logo_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
