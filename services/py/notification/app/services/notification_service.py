from __future__ import annotations

from uuid import UUID

import structlog

from common.errors import NotFoundError
from app.adapters.email import EmailClient
from app.adapters.ws_client import WsPublisher
from app.domain.notification import (
    EMAIL_SUBJECTS,
    EMAIL_TRIGGERING_TYPES,
    Notification,
    NotificationType,
)
from app.repositories.notification_repo import NotificationRepository
from app.templates import get_email_template

logger = structlog.get_logger()


class NotificationService:
    def __init__(
        self,
        repo: NotificationRepository,
        email_adapter: EmailClient | None = None,
        ws_publisher: WsPublisher | None = None,
    ) -> None:
        self._repo = repo
        self._email_adapter = email_adapter
        self._ws_publisher = ws_publisher

    async def create(
        self,
        user_id: UUID,
        type: NotificationType,
        title: str,
        body: str,
        email: str | None = None,
        organization_id: UUID | None = None,
        template_kwargs: dict | None = None,
        event_id: str | None = None,
    ) -> Notification | None:
        if event_id is not None:
            if await self._repo.exists_by_event_id(event_id):
                logger.info("event_already_processed", event_id=event_id)
                return None

        email_sent = False

        if (
            email
            and self._email_adapter
            and type in EMAIL_TRIGGERING_TYPES
        ):
            subject = EMAIL_SUBJECTS[type]
            html_body = body
            if template_kwargs is not None:
                rendered = get_email_template(str(type), **template_kwargs)
                if rendered is not None:
                    subject, html_body = rendered
            try:
                email_sent = await self._email_adapter.send(
                    to=email,
                    subject=subject,
                    html_body=html_body,
                )
            except Exception:
                logger.warning(
                    "email_send_failed",
                    user_id=str(user_id),
                    type=str(type),
                    email=email,
                )
                email_sent = False

        notification = await self._repo.create(
            user_id, type, title, body, email_sent, organization_id, event_id=event_id,
        )
        logger.info(
            "notification_created",
            user_id=str(user_id),
            type=str(type),
            title=title,
            email_sent=email_sent,
        )

        if self._ws_publisher:
            await self._ws_publisher.publish_notification(
                str(user_id),
                {
                    "id": str(notification.id),
                    "notification_type": str(notification.type),
                    "title": notification.title,
                    "body": notification.body,
                },
            )

        return notification

    async def list_my(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Notification], int]:
        return await self._repo.list_by_user(user_id, limit, offset)

    async def list_by_org(
        self, organization_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Notification], int]:
        return await self._repo.list_by_org(organization_id, limit, offset)

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
            logger.info("streak_reminder_sent", user_id=str(uid))
            sent += 1
        return sent

    async def send_flashcard_reminders(
        self, items: list[dict],
    ) -> int:
        sent = 0
        for item in items:
            uid = item["user_id"]
            card_count = item["card_count"]
            has_existing = await self._repo.has_unread_by_type(
                uid, NotificationType.FLASHCARD_REMINDER,
            )
            if has_existing:
                continue
            await self._repo.create(
                uid,
                NotificationType.FLASHCARD_REMINDER,
                "Flashcards due for review!",
                f"You have {card_count} flashcards due for review!",
            )
            logger.info("flashcard_reminder_sent", user_id=str(uid), card_count=card_count)
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
