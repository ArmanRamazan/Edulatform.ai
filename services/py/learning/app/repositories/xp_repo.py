from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.xp import XpEvent

_COLUMNS = "id, user_id, action, points, course_id, created_at"


class XpRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_event(
        self,
        user_id: UUID,
        action: str,
        points: int,
        course_id: UUID | None = None,
    ) -> XpEvent:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO xp_events (user_id, action, points, course_id)
            VALUES ($1, $2, $3, $4)
            RETURNING {_COLUMNS}
            """,
            user_id, action, points, course_id,
        )
        return self._to_event(row)

    async def get_total(self, user_id: UUID) -> int:
        total = await self._pool.fetchval(
            "SELECT COALESCE(SUM(points), 0) FROM xp_events WHERE user_id = $1",
            user_id,
        )
        return int(total)

    async def get_history(
        self, user_id: UUID, limit: int, offset: int,
    ) -> list[XpEvent]:
        rows = await self._pool.fetch(
            f"""
            SELECT {_COLUMNS} FROM xp_events
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id, limit, offset,
        )
        return [self._to_event(row) for row in rows]

    @staticmethod
    def _to_event(row: asyncpg.Record) -> XpEvent:
        return XpEvent(
            id=row["id"],
            user_id=row["user_id"],
            action=row["action"],
            points=row["points"],
            course_id=row["course_id"],
            created_at=row["created_at"],
        )
