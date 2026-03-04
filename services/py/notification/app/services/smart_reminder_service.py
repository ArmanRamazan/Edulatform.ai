from __future__ import annotations

from uuid import UUID

import httpx
import structlog

from common.security import create_access_token
from app.domain.notification import NotificationType
from app.repositories.notification_repo import NotificationRepository

logger = structlog.get_logger()

DUE_CARDS_THRESHOLD = 5
ACTIVE_STREAK_THRESHOLD = 3
HTTP_TIMEOUT = 5.0


class SmartReminderService:
    def __init__(
        self,
        repo: NotificationRepository,
        http_client: httpx.AsyncClient,
        learning_service_url: str,
        jwt_secret: str,
    ) -> None:
        self._repo = repo
        self._http = http_client
        self._base_url = learning_service_url.rstrip("/")
        self._jwt_secret = jwt_secret

    async def send_smart_reminders(self) -> dict[str, int]:
        user_ids = await self._repo.get_distinct_user_ids()

        stats = {
            "users_checked": len(user_ids),
            "reminders_sent": 0,
            "skipped_active_streak": 0,
            "skipped_low_cards": 0,
            "skipped_existing": 0,
            "skipped_errors": 0,
        }

        for uid in user_ids:
            try:
                await self._process_user(uid, stats)
            except Exception:
                logger.warning("smart_reminder_user_error", user_id=str(uid), exc_info=True)
                stats["skipped_errors"] += 1

        logger.info("smart_reminders_completed", **stats)
        return stats

    async def _process_user(self, user_id: UUID, stats: dict[str, int]) -> None:
        has_existing = await self._repo.has_unread_by_type(
            user_id, NotificationType.FLASHCARD_REMINDER,
        )
        if has_existing:
            stats["skipped_existing"] += 1
            return

        due_count = await self._get_due_count(user_id)
        if due_count <= DUE_CARDS_THRESHOLD:
            stats["skipped_low_cards"] += 1
            return

        streak = await self._get_streak(user_id)
        if streak["current_streak"] > ACTIVE_STREAK_THRESHOLD and streak["active_today"]:
            stats["skipped_active_streak"] += 1
            return

        await self._repo.create(
            user_id,
            NotificationType.FLASHCARD_REMINDER,
            "Время для повторения!",
            f"У вас {due_count} карточек для повторения. Не дайте знаниям забыться!",
        )
        logger.info("smart_reminder_sent", user_id=str(user_id), due_count=due_count)
        stats["reminders_sent"] += 1

    async def _get_due_count(self, user_id: UUID) -> int:
        token = self._make_service_token(user_id)
        resp = await self._http.get(
            f"{self._base_url}/flashcards/due",
            params={"limit": 1, "offset": 0},
            headers={"Authorization": f"Bearer {token}"},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["total"]

    async def _get_streak(self, user_id: UUID) -> dict:
        token = self._make_service_token(user_id)
        resp = await self._http.get(
            f"{self._base_url}/streaks/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _make_service_token(self, user_id: UUID) -> str:
        return create_access_token(
            str(user_id),
            self._jwt_secret,
            extra_claims={"role": "student", "is_verified": False},
        )
