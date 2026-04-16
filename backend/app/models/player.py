from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from beanie import Document
from pydantic import BaseModel, Field


class PlayerRole(str, Enum):
    batsman = "batsman"
    bowler = "bowler"
    all_rounder = "all_rounder"
    wicket_keeper = "wicket_keeper"


class BattingStyle(str, Enum):
    right_hand = "right_hand"
    left_hand = "left_hand"


class BowlingStyle(str, Enum):
    right_arm_fast = "right_arm_fast"
    right_arm_medium = "right_arm_medium"
    left_arm_fast = "left_arm_fast"
    left_arm_medium = "left_arm_medium"
    right_arm_spin = "right_arm_spin"
    left_arm_spin = "left_arm_spin"
    none = "none"


class PlayerStats(BaseModel):
    matches: int = 0
    runs: int = 0
    wickets: int = 0
    average: float = 0.0
    strike_rate: float = 0.0
    economy_rate: float = 0.0
    centuries: int = 0
    half_centuries: int = 0
    five_wicket_hauls: int = 0


class Player(Document):
    name: str
    country: str = "India"
    age: Optional[int] = None
    role: PlayerRole = PlayerRole.batsman
    batting_style: BattingStyle = BattingStyle.right_hand
    bowling_style: BowlingStyle = BowlingStyle.none
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    base_price: float = 100_000.0  # 1 lakh default
    stats: PlayerStats = Field(default_factory=PlayerStats)
    team_id: Optional[str] = None  # assigned after auction
    is_available: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "players"
