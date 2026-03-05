from __future__ import annotations

from uuid import UUID

import structlog

from app.domain.mission import Mission
from app.services.flashcard_service import FlashcardService

logger = structlog.get_logger()


class ReviewGenerator:
    def __init__(self, flashcard_service: FlashcardService) -> None:
        self._flashcard_service = flashcard_service

    async def generate_from_mission(
        self, user_id: UUID, mission: Mission,
    ) -> list[UUID]:
        blueprint = mission.blueprint
        cards: list[UUID] = []

        pairs = self._extract_pairs(blueprint)
        for concept, answer in pairs:
            try:
                card = await self._flashcard_service.create_card(
                    student_id=user_id,
                    role="student",
                    course_id=mission.organization_id,
                    concept=concept,
                    answer=answer,
                    source_type="mission",
                    source_id=mission.id,
                )
                cards.append(card.id)
            except Exception:
                logger.warning(
                    "flashcard_creation_failed",
                    user_id=str(user_id),
                    mission_id=str(mission.id),
                    concept=concept,
                )

        return cards

    @staticmethod
    def _extract_pairs(blueprint: dict) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []

        for q in blueprint.get("check_questions", []):
            question = q.get("question", "")
            explanation = q.get("explanation", "")
            if question and explanation:
                pairs.append((question, explanation))

        code_case = blueprint.get("code_case")
        if code_case:
            question = code_case.get("question", "")
            expected = code_case.get("expected_answer", "")
            if question and expected:
                pairs.append((question, expected))

        return pairs
