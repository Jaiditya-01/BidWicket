from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class TeamCreate(BaseModel):
    name: str
    short_name: Optional[str] = None
    tournament_id: Optional[str] = None
    budget: float = 10_000_000.0
    logo_url: Optional[str] = None
    home_ground: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    logo_url: Optional[str] = None
    home_ground: Optional[str] = None
    budget: Optional[float] = None


class TeamOut(BaseModel):
    id: str
    name: str
    short_name: Optional[str]
    owner_id: str
    tournament_id: Optional[str]
    budget: float
    remaining_budget: float
    logo_url: Optional[str]
    home_ground: Optional[str]
    players: List[str]
    created_at: datetime

    class Config:
        from_attributes = True
