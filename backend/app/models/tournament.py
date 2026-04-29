from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from beanie import Document
from pydantic import Field


class TournamentType(str, Enum):
    league = "league"
    knockout = "knockout"
    hybrid = "hybrid"
    t20 = "t20"
    odi = "odi"
    test = "test"

# status of the Tournament in the Tournament and Dashboard when Live (Ongoing)
class TournamentStatus(str, Enum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    completed = "completed"
    cancelled = "cancelled"


class Tournament(Document):
    name: str
    description: Optional[str] = None
    tournament_type: TournamentType = TournamentType.league
    status: TournamentStatus = TournamentStatus.upcoming
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    organizer_id: Optional[str] = None  # User id
    max_teams: int = 8
    logo_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "tournaments"
