from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.notification import NotificationType


class NotificationOut(BaseModel):
    id: str
    user_id: str
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool
    related_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    success: bool


class MarkAllReadResponse(BaseModel):
    success: bool


class NotificationsListResponse(BaseModel):
    items: List[NotificationOut]
