from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.leaderboard import LeaderboardEntry

_COLUMNS = "id, student_id, course_id, score, opted_in, updated_at"


class LeaderboardRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def opt_in(self, student_id: UUID, course_id: UUID) -> LeaderboardEntry:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO leaderboard_entries (student_id, course_id, opted_in)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (student_id, course_id) DO UPDATE
                SET opted_in = TRUE, updated_at = now()
            RETURNING {_COLUMNS}
            """,
            student_id, course_id,
        )
        return self._to_entry(row)

    async def opt_out(self, student_id: UUID, course_id: UUID) -> LeaderboardEntry | None:
        row = await self._pool.fetchrow(
            f"""
            UPDATE leaderboard_entries
            SET opted_in = FALSE, updated_at = now()
            WHERE student_id = $1 AND course_id = $2
            RETURNING {_COLUMNS}
            """,
            student_id, course_id,
        )
        return self._to_entry(row) if row else None

    async def add_score(
        self, student_id: UUID, course_id: UUID, points: int,
    ) -> LeaderboardEntry | None:
        row = await self._pool.fetchrow(
            f"""
            UPDATE leaderboard_entries
            SET score = score + $3, updated_at = now()
            WHERE student_id = $1 AND course_id = $2
            RETURNING {_COLUMNS}
            """,
            student_id, course_id, points,
        )
        return self._to_entry(row) if row else None

    async def get_leaderboard(
        self, course_id: UUID, limit: int, offset: int,
    ) -> tuple[list[LeaderboardEntry], int]:
        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT count(*) FROM leaderboard_entries WHERE course_id = $1 AND opted_in = TRUE",
                course_id,
            )
            rows = await conn.fetch(
                f"""
                SELECT {_COLUMNS} FROM leaderboard_entries
                WHERE course_id = $1 AND opted_in = TRUE
                ORDER BY score DESC, updated_at ASC
                LIMIT $2 OFFSET $3
                """,
                course_id, limit, offset,
            )
        return [self._to_entry(row) for row in rows], total

    async def get_entry(
        self, student_id: UUID, course_id: UUID,
    ) -> LeaderboardEntry | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM leaderboard_entries WHERE student_id = $1 AND course_id = $2",
            student_id, course_id,
        )
        return self._to_entry(row) if row else None

    async def get_rank(self, student_id: UUID, course_id: UUID) -> int | None:
        rank = await self._pool.fetchval(
            """
            SELECT rank FROM (
                SELECT student_id, RANK() OVER (ORDER BY score DESC, updated_at ASC) as rank
                FROM leaderboard_entries
                WHERE course_id = $2 AND opted_in = TRUE
            ) ranked
            WHERE student_id = $1
            """,
            student_id, course_id,
        )
        return int(rank) if rank is not None else None

    @staticmethod
    def _to_entry(row: asyncpg.Record) -> LeaderboardEntry:
        return LeaderboardEntry(
            id=row["id"],
            student_id=row["student_id"],
            course_id=row["course_id"],
            score=row["score"],
            opted_in=row["opted_in"],
            updated_at=row["updated_at"],
        )
