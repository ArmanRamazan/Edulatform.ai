from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fsrs import Card, Rating, Scheduler, State

import structlog

from common.errors import ForbiddenError, NotFoundError
from app.domain.flashcard import Flashcard
from app.repositories.flashcard_repo import FlashcardRepository

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.activity_service import ActivityService

logger = structlog.get_logger()


class FlashcardService:
    def __init__(
        self, repo: FlashcardRepository, activity_service: ActivityService | None = None,
    ) -> None:
        self._repo = repo
        self._scheduler = Scheduler()
        self._activity_service = activity_service

    async def create_card(
        self,
        student_id: UUID,
        role: str,
        course_id: UUID,
        concept: str,
        answer: str,
        source_type: str | None = None,
        source_id: UUID | None = None,
    ) -> Flashcard:
        if role != "student":
            raise ForbiddenError("Only students can create flashcards")
        return await self._repo.create(
            student_id=student_id,
            course_id=course_id,
            concept=concept,
            answer=answer,
            source_type=source_type,
            source_id=source_id,
        )

    async def get_due_cards(
        self, student_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Flashcard], int]:
        now = datetime.now(timezone.utc)
        return await self._repo.get_due_cards(student_id, now, limit, offset)

    async def review_card(
        self,
        card_id: UUID,
        student_id: UUID,
        role: str,
        rating: int,
        review_duration_ms: int | None = None,
    ) -> tuple[Flashcard, dict]:
        """Review a flashcard using FSRS scheduling algorithm.

        Returns updated flashcard and scheduling info dict.
        """
        if role != "student":
            raise ForbiddenError("Only students can review flashcards")

        card_entity = await self._repo.get_by_id(card_id)
        if card_entity is None:
            raise NotFoundError("Flashcard not found")
        if card_entity.student_id != student_id:
            raise ForbiddenError("Not your flashcard")

        # Build FSRS Card from DB state.
        # fsrs v6 Card uses: state (enum), step, stability, difficulty,
        # due, last_review. DB state=0 means "new" (use fresh Card defaults).
        fsrs_card = Card()
        if card_entity.state != 0:
            fsrs_card.stability = card_entity.stability
            fsrs_card.difficulty = card_entity.difficulty
            fsrs_card.due = card_entity.due
            fsrs_card.last_review = card_entity.last_review
            fsrs_card.step = card_entity.reps
            fsrs_card.state = State(card_entity.state)

        # Run FSRS scheduling
        fsrs_rating = Rating(rating)
        new_card, _review_log = self._scheduler.review_card(fsrs_card, fsrs_rating)

        # Map FSRS card back to DB fields.
        # reps = step (learning step counter), lapses counted from state transitions.
        new_reps = new_card.step if new_card.step is not None else card_entity.reps
        new_lapses = card_entity.lapses
        if new_card.state == State.Relearning:
            new_lapses = card_entity.lapses + 1

        # Persist updated state
        updated = await self._repo.update_fsrs_state(
            card_id=card_id,
            stability=new_card.stability,
            difficulty=new_card.difficulty,
            due=new_card.due,
            last_review=new_card.last_review or datetime.now(timezone.utc),
            reps=new_reps,
            lapses=new_lapses,
            state=new_card.state.value,
        )

        # Log the review
        await self._repo.create_review_log(
            card_id=card_id,
            rating=rating,
            review_duration_ms=review_duration_ms,
        )

        if self._activity_service is not None:
            try:
                from app.domain.activity import ActivityType
                await self._activity_service.record(
                    user_id=student_id,
                    activity_type=ActivityType.flashcard_reviewed,
                    payload={"card_id": str(card_id), "rating": rating},
                )
            except Exception:
                logger.warning("activity_record_failed", card_id=str(card_id))

        scheduling_info = {
            "new_stability": new_card.stability,
            "new_difficulty": new_card.difficulty,
            "next_due": new_card.due,
            "new_state": new_card.state.value,
        }

        return updated, scheduling_info

    async def delete_card(
        self, card_id: UUID, student_id: UUID, role: str
    ) -> bool:
        if role != "student":
            raise ForbiddenError("Only students can delete flashcards")
        deleted = await self._repo.delete(card_id, student_id)
        if not deleted:
            raise NotFoundError("Flashcard not found or not yours")
        return True
