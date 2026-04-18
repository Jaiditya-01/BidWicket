from typing import List

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser
from app.models.notification import Notification
from app.schemas.notification import (
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationsListResponse,
    NotificationOut,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=str(n.id),
        user_id=n.user_id,
        notification_type=n.notification_type,
        title=n.title,
        message=n.message,
        is_read=n.is_read,
        related_id=n.related_id,
        created_at=n.created_at,
    )


@router.get("/", response_model=NotificationsListResponse)
async def list_notifications(current_user: CurrentUser, limit: int = 50, skip: int = 0):
    limit = max(1, min(200, limit))
    skip = max(0, skip)
    items = (
        await Notification.find(Notification.user_id == str(current_user.id))
        .sort(-Notification.created_at)
        .skip(skip)
        .limit(limit)
        .to_list()
    )
    return NotificationsListResponse(items=[_out(n) for n in items])


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(current_user: CurrentUser):
    count = await Notification.find(
        Notification.user_id == str(current_user.id),
        Notification.is_read == False,
    ).count()
    return UnreadCountResponse(unread_count=count)


@router.post("/{notification_id}/read", response_model=MarkReadResponse)
async def mark_read(notification_id: str, current_user: CurrentUser):
    n = await Notification.get(notification_id)
    if not n or n.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Notification not found")
    if not n.is_read:
        await n.set({"is_read": True})
    return MarkReadResponse(success=True)


@router.post("/read-all", response_model=MarkAllReadResponse, status_code=status.HTTP_200_OK)
async def mark_all_read(current_user: CurrentUser):
    await Notification.find(
        Notification.user_id == str(current_user.id),
        Notification.is_read == False,
    ).update({"$set": {"is_read": True}})
    return MarkAllReadResponse(success=True)
