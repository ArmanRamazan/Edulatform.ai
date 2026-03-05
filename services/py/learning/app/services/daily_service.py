from __future__ import annotations

import asyncio
from uuid import UUID

from app.domain.daily import DailySummary
from app.services.mission_service import MissionService
from app.services.trust_level_service import TrustLevelService
from app.services.flashcard_service import FlashcardService
from app.services.streak_service import StreakService


class DailyService:
    def __init__(
        self,
        mission_service: MissionService,
        trust_level_service: TrustLevelService,
        flashcard_service: FlashcardService,
        streak_service: StreakService,
    ) -> None:
        self._mission_service = mission_service
        self._trust_level_service = trust_level_service
        self._flashcard_service = flashcard_service
        self._streak_service = streak_service

    async def get_daily_summary(
        self, user_id: UUID, org_id: UUID, *, token: str,
    ) -> DailySummary:
        mission, trust_level, due_result, streak_resp = await asyncio.gather(
            self._mission_service.get_or_create_today(user_id, org_id, token=token),
            self._trust_level_service.get_my_level(user_id, org_id),
            self._flashcard_service.get_due_cards(user_id),
            self._streak_service.get_streak(user_id),
        )

        due_flashcards = due_result[1] if isinstance(due_result, tuple) else 0
        streak_days = streak_resp.current_streak

        concept_name = None
        if mission is not None:
            concept_name = mission.blueprint.get("concept_name")

        greeting = _build_greeting(streak_days, concept_name)

        return DailySummary(
            mission=mission,
            trust_level=trust_level,
            due_flashcards=due_flashcards,
            streak_days=streak_days,
            greeting=greeting,
        )


def _build_greeting(streak_days: int, concept_name: str | None) -> str:
    if streak_days > 0 and concept_name:
        return f"Day {streak_days}. Today's topic: {concept_name}."
    if streak_days > 0:
        return f"Day {streak_days}. Welcome back!"
    if concept_name:
        return f"Welcome! Today's topic: {concept_name}."
    return "Welcome! Let's get started."
