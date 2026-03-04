from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import asyncpg

from common.errors import ConflictError
from app.domain.review import Review


class ReviewRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self, student_id: UUID, course_id: UUID, rating: int, comment: str
    ) -> Review:
        try:
            row = await self._pool.fetchrow(
                """
                INSERT INTO reviews (student_id, course_id, rating, comment)
                VALUES ($1, $2, $3, $4)
                RETURNING id, student_id, course_id, rating, comment, created_at
                """,
                student_id,
                course_id,
                rating,
                comment,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("You already reviewed this course") from exc
        return self._to_entity(row)

    async def list_by_course(
        self, course_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Review], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, student_id, course_id, rating, comment, created_at
                FROM reviews WHERE course_id = $1
                ORDER BY created_at DESC LIMIT $2 OFFSET $3
                """,
                course_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM reviews WHERE course_id = $1",
                course_id,
            )
        return [self._to_entity(r) for r in rows], count

    async def get_avg(self, course_id: UUID) -> tuple[Decimal | None, int]:
        row = await self._pool.fetchrow(
            "SELECT AVG(rating)::NUMERIC(3,2) as avg_rating, count(*) as cnt FROM reviews WHERE course_id = $1",
            course_id,
        )
        return row["avg_rating"], row["cnt"]

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Review:
        return Review(
            id=row["id"],
            student_id=row["student_id"],
            course_id=row["course_id"],
            rating=row["rating"],
            comment=row["comment"],
            created_at=row["created_at"],
        )
