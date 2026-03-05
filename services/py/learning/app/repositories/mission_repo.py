from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import asyncpg

from app.domain.mission import Mission

_COLUMNS = (
    "id, user_id, organization_id, concept_id, mission_type, status, "
    "blueprint, score, mastery_delta, started_at, completed_at, created_at"
)


class MissionRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        user_id: UUID,
        organization_id: UUID,
        concept_id: UUID | None,
        mission_type: str,
        blueprint: dict,
    ) -> Mission:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO missions (user_id, organization_id, concept_id, mission_type, blueprint)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING {_COLUMNS}
            """,
            user_id,
            organization_id,
            concept_id,
            mission_type,
            json.dumps(blueprint),
        )
        return self._to_mission(row)

    async def get_by_id(self, mission_id: UUID) -> Mission | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM missions WHERE id = $1",
            mission_id,
        )
        return self._to_mission(row) if row else None

    async def get_by_user(
        self, user_id: UUID, limit: int = 20, offset: int = 0,
    ) -> list[Mission]:
        rows = await self._pool.fetch(
            f"""
            SELECT {_COLUMNS} FROM missions
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )
        return [self._to_mission(row) for row in rows]

    async def get_today(self, user_id: UUID) -> Mission | None:
        row = await self._pool.fetchrow(
            f"""
            SELECT {_COLUMNS} FROM missions
            WHERE user_id = $1
              AND created_at::date = CURRENT_DATE
              AND status != 'skipped'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id,
        )
        return self._to_mission(row) if row else None

    async def update_status(
        self,
        mission_id: UUID,
        status: str,
        score: float | None = None,
        mastery_delta: float | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> Mission:
        row = await self._pool.fetchrow(
            f"""
            UPDATE missions
            SET status = $2,
                score = COALESCE($3, score),
                mastery_delta = COALESCE($4, mastery_delta),
                started_at = COALESCE($5, started_at),
                completed_at = COALESCE($6, completed_at)
            WHERE id = $1
            RETURNING {_COLUMNS}
            """,
            mission_id,
            status,
            score,
            mastery_delta,
            started_at,
            completed_at,
        )
        return self._to_mission(row)

    async def get_streak(self, user_id: UUID) -> int:
        result = await self._pool.fetchval(
            """
            WITH completed_dates AS (
                SELECT DISTINCT created_at::date AS d
                FROM missions
                WHERE user_id = $1 AND status = 'completed'
            ),
            streak AS (
                SELECT d, d - (ROW_NUMBER() OVER (ORDER BY d))::int AS grp
                FROM completed_dates
            ),
            streaks AS (
                SELECT grp, COUNT(*) AS len, MAX(d) AS last_day
                FROM streak
                GROUP BY grp
            )
            SELECT COALESCE(len, 0)
            FROM streaks
            WHERE last_day = CURRENT_DATE
               OR last_day = CURRENT_DATE - 1
            ORDER BY last_day DESC
            LIMIT 1
            """,
            user_id,
        )
        return result or 0

    @staticmethod
    def _to_mission(row: asyncpg.Record) -> Mission:
        blueprint = row["blueprint"]
        if isinstance(blueprint, str):
            blueprint = json.loads(blueprint)
        elif blueprint is None:
            blueprint = {}

        return Mission(
            id=row["id"],
            user_id=row["user_id"],
            organization_id=row["organization_id"],
            concept_id=row["concept_id"],
            mission_type=row["mission_type"],
            status=row["status"],
            blueprint=blueprint,
            score=row["score"],
            mastery_delta=row["mastery_delta"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            created_at=row["created_at"],
        )
