from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.player import PlayerRole, BattingStyle, BowlingStyle, PlayerStats


class PlayerCreate(BaseModel):
    name: str
    country: str = "India"
    age: Optional[int] = None
    role: PlayerRole = PlayerRole.batsman
    batting_style: BattingStyle = BattingStyle.right_hand
    bowling_style: BowlingStyle = BowlingStyle.none
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    base_price: float = 100_000.0
    stats: Optional[PlayerStats] = None


class PlayerUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    age: Optional[int] = None
    role: Optional[PlayerRole] = None
    batting_style: Optional[BattingStyle] = None
    bowling_style: Optional[BowlingStyle] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    base_price: Optional[float] = None
    stats: Optional[PlayerStats] = None
    is_available: Optional[bool] = None


class PlayerOut(BaseModel):
    id: str
    name: str
    country: str
    age: Optional[int]
    role: PlayerRole
    batting_style: BattingStyle
    bowling_style: BowlingStyle
    bio: Optional[str]
    photo_url: Optional[str]
    base_price: float
    stats: PlayerStats
    team_id: Optional[str]
    is_available: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PlayerStatsOut(BaseModel):
    player_id: str
    name: str
    matches: int
    runs: int
    wickets: int
    average: float
    strike_rate: float
    economy_rate: float
    centuries: int
    half_centuries: int
    five_wicket_hauls: int

    class Config:
        from_attributes = True
