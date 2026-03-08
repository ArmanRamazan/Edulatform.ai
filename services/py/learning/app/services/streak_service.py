from __future__ import annotations

import json
import uuid as _uuid_module
from datetime import date, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from common.nats import NATSClient
from app.domain.streak import Streak, StreakResponse
from app.repositories.streak_repo import StreakRepository

if TYPE_CHECKING:
    from app.services.activity_service import ActivityService

logger = structlog.get_logger()

_STREAK_MILESTONES = frozenset({7, 14, 30, 60, 90, 180, 365})


class StreakService:
    def __init__(
        self,
        repo: StreakRepository,
        activity_service: ActivityService | None = None,
        nats_client: NATSClient | None = None,
    ) -> None:
        self._repo = repo
        self._activity_service = activity_service
        self._nats_client = nats_client

    async def record_activity(self, user_id: UUID) -> Streak:
        existing = await self._repo.get_by_user(user_id)

        if existing is None:
            return await self._repo.upsert(
                user_id=user_id, current_streak=1, longest_streak=1,
            )

        today = date.today()
        if existing.last_activity_date == today:
            return existing

        yesterday = today - timedelta(days=1)
        if existing.last_activity_date == yesterday:
            new_current = existing.current_streak + 1
        else:
            new_current = 1

        new_longest = max(new_current, existing.longest_streak)

        streak = await self._repo.upsert(
            user_id=user_id,
            current_streak=new_current,
            longest_streak=new_longest,
        )

        if self._activity_service is not None and new_current in _STREAK_MILESTONES:
            try:
                from app.domain.activity import ActivityType
                await self._activity_service.record(
                    user_id=user_id,
                    activity_type=ActivityType.streak_milestone,
                    payload={"streak": new_current},
                )
            except Exception:
                logger.warning("activity_record_failed", streak=new_current)

        if self._nats_client is not None and new_current in _STREAK_MILESTONES:
            try:
                event = {
                    "event_id": str(_uuid_module.uuid4()),
                    "user_id": str(user_id),
                    "streak": new_current,
                    "timestamp": date.today().isoformat(),
                }
                await self._nats_client.publish(
                    "platform.streak.milestone", json.dumps(event).encode()
                )
            except Exception:
                logger.warning(
                    "nats_publish_failed",
                    subject="platform.streak.milestone",
                    streak=new_current,
                )

        return streak

    async def get_at_risk_user_ids(self) -> list[UUID]:
        return await self._repo.get_at_risk_user_ids(date.today())

    async def get_streak(self, user_id: UUID) -> StreakResponse:
        existing = await self._repo.get_by_user(user_id)

        if existing is None:
            return StreakResponse(
                current_streak=0,
                longest_streak=0,
                last_activity_date=None,
                active_today=False,
            )

        today = date.today()
        yesterday = today - timedelta(days=1)
        is_alive = existing.last_activity_date >= yesterday
        active_today = existing.last_activity_date == today

        return StreakResponse(
            current_streak=existing.current_streak if is_alive else 0,
            longest_streak=existing.longest_streak,
            last_activity_date=existing.last_activity_date,
            active_today=active_today,
        )
