from __future__ import annotations

from typing import Optional

from app.models.notification import Notification, NotificationType


class NotificationService:
    async def create(
        self,
        *,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        related_id: Optional[str] = None,
    ) -> Notification:
        n = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            related_id=related_id,
        )
        await n.insert()
        return n


notification_service = NotificationService()
