from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from beanie import Document
from pydantic import Field


class NotificationType(str, Enum):
    auction_start = "auction_start"
    bid_placed = "bid_placed"
    player_sold = "player_sold"
    outbid = "outbid"
    match_start = "match_start"
    match_result = "match_result"
    system = "system"


class Notification(Document):
    user_id: str
    notification_type: NotificationType = NotificationType.system
    title: str
    message: str
    is_read: bool = False
    related_id: Optional[str] = None  # auction/match/player id
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "notifications"
