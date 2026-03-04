from __future__ import annotations

from uuid import UUID

import asyncpg

from common.errors import ConflictError
from app.domain.wishlist import WishlistItem


class WishlistRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def add(self, user_id: UUID, course_id: UUID) -> WishlistItem:
        try:
            row = await self._pool.fetchrow(
                """
                INSERT INTO wishlist (user_id, course_id)
                VALUES ($1, $2)
                RETURNING id, user_id, course_id, created_at
                """,
                user_id,
                course_id,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("Course already in wishlist") from exc

        course_row = await self._pool.fetchrow(
            "SELECT title, description FROM courses WHERE id = $1",
            course_id,
        )
        return WishlistItem(
            id=row["id"],
            user_id=row["user_id"],
            course_id=row["course_id"],
            course_title=course_row["title"],
            course_description=course_row["description"],
            created_at=row["created_at"],
        )

    async def remove(self, user_id: UUID, course_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM wishlist WHERE user_id = $1 AND course_id = $2",
            user_id,
            course_id,
        )
        return result == "DELETE 1"

    async def get_by_user(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[WishlistItem], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT w.id, w.user_id, w.course_id, w.created_at,
                       c.title AS course_title, c.description AS course_description
                FROM wishlist w
                JOIN courses c ON c.id = w.course_id
                WHERE w.user_id = $1
                ORDER BY w.created_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM wishlist WHERE user_id = $1",
                user_id,
            )
        return [self._to_entity(r) for r in rows], count

    async def exists(self, user_id: UUID, course_id: UUID) -> bool:
        val = await self._pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM wishlist WHERE user_id = $1 AND course_id = $2)",
            user_id,
            course_id,
        )
        return val

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> WishlistItem:
        return WishlistItem(
            id=row["id"],
            user_id=row["user_id"],
            course_id=row["course_id"],
            course_title=row["course_title"],
            course_description=row["course_description"],
            created_at=row["created_at"],
        )
