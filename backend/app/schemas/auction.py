from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.auction import AuctionStatus, AuctionItemStatus


class AuctionCreate(BaseModel):
    tournament_id: str
    name: str
    bid_timer_seconds: int = 30
    scheduled_at: Optional[datetime] = None


class AuctionUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[AuctionStatus] = None
    bid_timer_seconds: Optional[int] = None
    scheduled_at: Optional[datetime] = None


class AuctionOut(BaseModel):
    id: str
    tournament_id: str
    name: str
    status: AuctionStatus
    bid_timer_seconds: int
    current_item_id: Optional[str]
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AuctionItemCreate(BaseModel):
    auction_id: str
    player_id: str
    base_price: float


class AuctionItemOut(BaseModel):
    id: str
    auction_id: str
    player_id: str
    base_price: float
    current_bid: float
    highest_bidder_id: Optional[str]
    winning_team_id: Optional[str]
    status: AuctionItemStatus
    bid_count: int
    activated_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    sold_at: Optional[datetime]
    finalized_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlaceBidRequest(BaseModel):
    amount: float
    team_id: str


class ForceSellRequest(BaseModel):
    team_id: str
    amount: Optional[float] = None


class ResetTimerRequest(BaseModel):
    seconds: int


class BidOut(BaseModel):
    id: str
    auction_item_id: str
    auction_id: str
    user_id: str
    team_id: str
    amount: float
    is_winning: bool
    timestamp: datetime

    class Config:
        from_attributes = True
