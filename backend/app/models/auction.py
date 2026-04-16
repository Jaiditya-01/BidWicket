from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from beanie import Document
from pydantic import Field


class AuctionStatus(str, Enum):
    upcoming = "upcoming"
    live = "live"
    paused = "paused"
    completed = "completed"


class AuctionItemStatus(str, Enum):
    pending = "pending"
    active = "active"
    sold = "sold"
    unsold = "unsold"


class Auction(Document):
    tournament_id: str
    name: str
    status: AuctionStatus = AuctionStatus.upcoming
    bid_timer_seconds: int = 30  # countdown per item
    current_item_id: Optional[str] = None  # active AuctionItem id
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "auctions"


class AuctionItem(Document):
    auction_id: str
    player_id: str
    base_price: float
    current_bid: float = 0.0
    highest_bidder_id: Optional[str] = None  # User id (team owner)
    winning_team_id: Optional[str] = None
    status: AuctionItemStatus = AuctionItemStatus.pending
    bid_count: int = 0
    sold_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "auction_items"


class Bid(Document):
    auction_item_id: str
    auction_id: str
    user_id: str       # bidder (team owner)
    team_id: str
    amount: float
    is_winning: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "bids"
