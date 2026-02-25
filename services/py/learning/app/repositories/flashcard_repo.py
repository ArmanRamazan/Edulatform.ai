from __future__ import annotations

from datetime import datetime
from uuid import UUID

import asyncpg

from app.domain.flashcard import Flashcard, ReviewLog

_FLASHCARD_COLUMNS = (
    "id, student_id, course_id, concept, answer, source_type, source_id, "
    "stability, difficulty, due, last_review, reps, lapses, state, created_at"
)
_REVIEW_LOG_COLUMNS = "id, card_id, rating, review_duration_ms, reviewed_at"


class FlashcardRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        student_id: UUID,
        course_id: UUID,
        concept: str,
        answer: str,
        source_type: str | None = None,
        source_id: UUID | None = None,
    ) -> Flashcard:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO flashcards (student_id, course_id, concept, answer, source_type, source_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING {_FLASHCARD_COLUMNS}
            """,
            student_id, course_id, concept, answer, source_type, source_id,
        )
        return self._to_flashcard(row)

    async def get_by_id(self, card_id: UUID) -> Flashcard | None:
        row = await self._pool.fetchrow(
            f"SELECT {_FLASHCARD_COLUMNS} FROM flashcards WHERE id = $1",
            card_id,
        )
        return self._to_flashcard(row) if row else None

    async def get_due_cards(
        self, student_id: UUID, now: datetime, limit: int = 20, offset: int = 0
    ) -> tuple[list[Flashcard], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT {_FLASHCARD_COLUMNS} FROM flashcards
                WHERE student_id = $1 AND due <= $2
                ORDER BY due ASC LIMIT $3 OFFSET $4
                """,
                student_id, now, limit, offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM flashcards WHERE student_id = $1 AND due <= $2",
                student_id, now,
            )
        return [self._to_flashcard(r) for r in rows], count

    async def update_fsrs_state(
        self,
        card_id: UUID,
        stability: float,
        difficulty: float,
        due: datetime,
        last_review: datetime,
        reps: int,
        lapses: int,
        state: int,
    ) -> Flashcard | None:
        row = await self._pool.fetchrow(
            f"""
            UPDATE flashcards
            SET stability = $2, difficulty = $3, due = $4, last_review = $5,
                reps = $6, lapses = $7, state = $8
            WHERE id = $1
            RETURNING {_FLASHCARD_COLUMNS}
            """,
            card_id, stability, difficulty, due, last_review, reps, lapses, state,
        )
        return self._to_flashcard(row) if row else None

    async def create_review_log(
        self,
        card_id: UUID,
        rating: int,
        review_duration_ms: int | None = None,
    ) -> ReviewLog:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO review_logs (card_id, rating, review_duration_ms)
            VALUES ($1, $2, $3)
            RETURNING {_REVIEW_LOG_COLUMNS}
            """,
            card_id, rating, review_duration_ms,
        )
        return self._to_review_log(row)

    async def count_by_student(self, student_id: UUID) -> int:
        return await self._pool.fetchval(
            "SELECT count(*) FROM flashcards WHERE student_id = $1",
            student_id,
        )

    async def delete(self, card_id: UUID, student_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM flashcards WHERE id = $1 AND student_id = $2",
            card_id, student_id,
        )
        return result == "DELETE 1"

    @staticmethod
    def _to_flashcard(row: asyncpg.Record) -> Flashcard:
        return Flashcard(
            id=row["id"],
            student_id=row["student_id"],
            course_id=row["course_id"],
            concept=row["concept"],
            answer=row["answer"],
            source_type=row["source_type"],
            source_id=row["source_id"],
            stability=row["stability"],
            difficulty=row["difficulty"],
            due=row["due"],
            last_review=row["last_review"],
            reps=row["reps"],
            lapses=row["lapses"],
            state=row["state"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_review_log(row: asyncpg.Record) -> ReviewLog:
        return ReviewLog(
            id=row["id"],
            card_id=row["card_id"],
            rating=row["rating"],
            review_duration_ms=row["review_duration_ms"],
            reviewed_at=row["reviewed_at"],
        )
