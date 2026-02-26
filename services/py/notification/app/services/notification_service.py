from __future__ import annotations

import logging
from uuid import UUID

from common.errors import NotFoundError
from app.domain.notification import Notification, NotificationType
from app.repositories.notification_repo import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, repo: NotificationRepository) -> None:
        self._repo = repo

    async def create(
        self,
        user_id: UUID,
        type: NotificationType,
        title: str,
        body: str,
    ) -> Notification:
        notification = await self._repo.create(user_id, type, title, body)
        logger.info(
            "[NOTIFICATION] user=%s type=%s title=%s",
            user_id, type, title,
        )
        return notification

    async def list_my(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Notification], int]:
        return await self._repo.list_by_user(user_id, limit, offset)

    async def send_streak_reminders(self, user_ids: list[UUID]) -> int:
        sent = 0
        for uid in user_ids:
            has_existing = await self._repo.has_unread_by_type(
                uid, NotificationType.STREAK_REMINDER,
            )
            if has_existing:
                continue
            await self._repo.create(
                uid,
                NotificationType.STREAK_REMINDER,
                "Your streak is at risk!",
                "You haven't studied today. Keep your streak alive!",
            )
            logger.info("[STREAK_REMINDER] user=%s", uid)
            sent += 1
        return sent

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        notification = await self._repo.get_by_id(notification_id)
        if not notification:
            raise NotFoundError("Notification not found")
        if notification.user_id != user_id:
            raise NotFoundError("Notification not found")
        updated = await self._repo.mark_as_read(notification_id)
        return updated
