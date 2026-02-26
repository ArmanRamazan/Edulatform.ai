from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.badge import Badge

_COLUMNS = "id, user_id, badge_type, unlocked_at"


class BadgeRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, user_id: UUID, badge_type: str) -> Badge:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO badges (user_id, badge_type)
            VALUES ($1, $2)
            ON CONFLICT (user_id, badge_type) DO NOTHING
            RETURNING {_COLUMNS}
            """,
            user_id, badge_type,
        )
        if row is None:
            return await self.get_by_type(user_id, badge_type)  # type: ignore[return-value]
        return self._to_badge(row)

    async def get_by_type(self, user_id: UUID, badge_type: str) -> Badge | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM badges WHERE user_id = $1 AND badge_type = $2",
            user_id, badge_type,
        )
        return self._to_badge(row) if row else None

    async def get_all(self, user_id: UUID) -> list[Badge]:
        rows = await self._pool.fetch(
            f"SELECT {_COLUMNS} FROM badges WHERE user_id = $1 ORDER BY unlocked_at DESC",
            user_id,
        )
        return [self._to_badge(row) for row in rows]

    @staticmethod
    def _to_badge(row: asyncpg.Record) -> Badge:
        return Badge(
            id=row["id"],
            user_id=row["user_id"],
            badge_type=row["badge_type"],
            unlocked_at=row["unlocked_at"],
        )
