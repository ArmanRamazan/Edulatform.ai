from __future__ import annotations

from uuid import UUID

import asyncpg

from common.errors import ConflictError
from app.domain.progress import LessonProgress


class ProgressRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def complete_lesson(
        self, student_id: UUID, lesson_id: UUID, course_id: UUID
    ) -> LessonProgress:
        try:
            row = await self._pool.fetchrow(
                """
                INSERT INTO lesson_progress (student_id, lesson_id, course_id)
                VALUES ($1, $2, $3)
                RETURNING id, student_id, lesson_id, course_id, completed_at
                """,
                student_id,
                lesson_id,
                course_id,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("Lesson already completed") from exc
        return self._to_entity(row)

    async def count_completed(self, student_id: UUID, course_id: UUID) -> int:
        count = await self._pool.fetchval(
            "SELECT count(*) FROM lesson_progress WHERE student_id = $1 AND course_id = $2",
            student_id,
            course_id,
        )
        return count

    async def list_completed_lessons(
        self, student_id: UUID, course_id: UUID
    ) -> list[UUID]:
        rows = await self._pool.fetch(
            "SELECT lesson_id FROM lesson_progress WHERE student_id = $1 AND course_id = $2",
            student_id,
            course_id,
        )
        return [row["lesson_id"] for row in rows]

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> LessonProgress:
        return LessonProgress(
            id=row["id"],
            student_id=row["student_id"],
            lesson_id=row["lesson_id"],
            course_id=row["course_id"],
            completed_at=row["completed_at"],
        )
