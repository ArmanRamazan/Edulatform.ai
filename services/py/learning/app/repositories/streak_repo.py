from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

import asyncpg

from app.domain.streak import Streak

_STREAK_COLUMNS = "user_id, current_streak, longest_streak, last_activity_date, updated_at"


class StreakRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_user(self, user_id: UUID) -> Streak | None:
        row = await self._pool.fetchrow(
            f"SELECT {_STREAK_COLUMNS} FROM streaks WHERE user_id = $1",
            user_id,
        )
        return self._to_streak(row) if row else None

    async def upsert(
        self,
        user_id: UUID,
        current_streak: int,
        longest_streak: int,
    ) -> Streak:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO streaks (user_id, current_streak, longest_streak, last_activity_date)
            VALUES ($1, $2, $3, CURRENT_DATE)
            ON CONFLICT (user_id) DO UPDATE
                SET current_streak = $2,
                    longest_streak = $3,
                    last_activity_date = CURRENT_DATE,
                    updated_at = now()
            RETURNING {_STREAK_COLUMNS}
            """,
            user_id, current_streak, longest_streak,
        )
        return self._to_streak(row)

    async def get_at_risk_user_ids(self, today: date) -> list[UUID]:
        yesterday = today - timedelta(days=1)
        rows = await self._pool.fetch(
            """
            SELECT user_id FROM streaks
            WHERE last_activity_date = $1
              AND current_streak >= 1
            """,
            yesterday,
        )
        return [row["user_id"] for row in rows]

    @staticmethod
    def _to_streak(row: asyncpg.Record) -> Streak:
        return Streak(
            user_id=row["user_id"],
            current_streak=row["current_streak"],
            longest_streak=row["longest_streak"],
            last_activity_date=row["last_activity_date"],
            updated_at=row["updated_at"],
        )
