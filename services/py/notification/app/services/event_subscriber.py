"""NATS event subscriber for notification service.

Subscribes to platform events and creates notification records.
All handlers are idempotent via event_id dedup.
"""
from __future__ import annotations

import json
from uuid import UUID

import structlog

from common.nats import NATSClient
from app.domain.notification import NotificationType
from app.services.notification_service import NotificationService

logger = structlog.get_logger()

_STREAM = "PLATFORM_EVENTS"


class NotificationEventSubscriber:
    """Subscribes to NATS events and creates notifications."""

    def __init__(
        self,
        nats_client: NATSClient,
        notification_service: NotificationService,
    ) -> None:
        self._nats = nats_client
        self._svc = notification_service

    async def start(self) -> None:
        """Register all subscriptions. Call once from lifespan."""
        await self._nats.subscribe(
            subject="platform.mission.completed",
            cb=self._handle_mission_completed,
            durable="notification-mission-completed",
            stream=_STREAM,
        )
        await self._nats.subscribe(
            subject="platform.badge.earned",
            cb=self._handle_badge_earned,
            durable="notification-badge-earned",
            stream=_STREAM,
        )
        await self._nats.subscribe(
            subject="platform.streak.milestone",
            cb=self._handle_streak_milestone,
            durable="notification-streak-milestone",
            stream=_STREAM,
        )
        logger.info("event_subscriber_started")

    async def _handle_mission_completed(self, msg: object) -> None:
        try:
            data = json.loads(msg.data)  # type: ignore[attr-defined]
            event_id: str = data["event_id"]
            user_id = UUID(data["user_id"])
            score: float = data.get("score", 0.0)
            await self._svc.create(
                user_id=user_id,
                type=NotificationType.MISSION_COMPLETED,
                title="Mission completed!",
                body=f"You completed today's mission with a score of {score:.0%}.",
                event_id=event_id,
            )
            await msg.ack()  # type: ignore[attr-defined]
        except Exception:
            logger.warning("handle_mission_completed_failed", exc_info=True)

    async def _handle_badge_earned(self, msg: object) -> None:
        try:
            data = json.loads(msg.data)  # type: ignore[attr-defined]
            event_id: str = data["event_id"]
            user_id = UUID(data["user_id"])
            badge_type: str = data["badge_type"]
            await self._svc.create(
                user_id=user_id,
                type=NotificationType.BADGE_EARNED,
                title="New badge earned!",
                body=f"You earned the '{badge_type}' badge. Keep it up!",
                event_id=event_id,
            )
            await msg.ack()  # type: ignore[attr-defined]
        except Exception:
            logger.warning("handle_badge_earned_failed", exc_info=True)

    async def _handle_streak_milestone(self, msg: object) -> None:
        try:
            data = json.loads(msg.data)  # type: ignore[attr-defined]
            event_id: str = data["event_id"]
            user_id = UUID(data["user_id"])
            streak: int = data["streak"]
            await self._svc.create(
                user_id=user_id,
                type=NotificationType.STREAK_MILESTONE,
                title=f"{streak}-day streak milestone!",
                body=f"Amazing! You've maintained a {streak}-day learning streak.",
                event_id=event_id,
            )
            await msg.ack()  # type: ignore[attr-defined]
        except Exception:
            logger.warning("handle_streak_milestone_failed", exc_info=True)
