from __future__ import annotations

import json
from uuid import UUID

import asyncpg

from app.domain.trust_level import TrustLevel

_COLUMNS = (
    "id, user_id, organization_id, level, "
    "total_missions_completed, total_concepts_mastered, "
    "unlocked_areas, level_up_at, created_at"
)


class TrustLevelRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_or_create(self, user_id: UUID, org_id: UUID) -> TrustLevel:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO trust_levels (user_id, organization_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
            RETURNING {_COLUMNS}
            """,
            user_id, org_id,
        )
        return self._to_entity(row)

    async def increment_missions(self, user_id: UUID) -> TrustLevel:
        row = await self._pool.fetchrow(
            f"""
            UPDATE trust_levels
            SET total_missions_completed = total_missions_completed + 1,
                updated_at = now()
            WHERE user_id = $1
            RETURNING {_COLUMNS}
            """,
            user_id,
        )
        return self._to_entity(row)

    async def increment_concepts(self, user_id: UUID) -> TrustLevel:
        row = await self._pool.fetchrow(
            f"""
            UPDATE trust_levels
            SET total_concepts_mastered = total_concepts_mastered + 1,
                updated_at = now()
            WHERE user_id = $1
            RETURNING {_COLUMNS}
            """,
            user_id,
        )
        return self._to_entity(row)

    async def update_level(
        self,
        user_id: UUID,
        new_level: int,
        unlocked_areas: list[str],
    ) -> TrustLevel:
        row = await self._pool.fetchrow(
            f"""
            UPDATE trust_levels
            SET level = $2,
                unlocked_areas = $3::jsonb,
                level_up_at = now(),
                updated_at = now()
            WHERE user_id = $1
            RETURNING {_COLUMNS}
            """,
            user_id, new_level, json.dumps(unlocked_areas),
        )
        return self._to_entity(row)

    async def get_by_org(
        self, org_id: UUID, limit: int, offset: int,
    ) -> list[TrustLevel]:
        rows = await self._pool.fetch(
            f"""
            SELECT {_COLUMNS} FROM trust_levels
            WHERE organization_id = $1
            ORDER BY level DESC, total_missions_completed DESC
            LIMIT $2 OFFSET $3
            """,
            org_id, limit, offset,
        )
        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> TrustLevel:
        unlocked = row["unlocked_areas"]
        if isinstance(unlocked, str):
            unlocked = json.loads(unlocked)
        return TrustLevel(
            id=row["id"],
            user_id=row["user_id"],
            organization_id=row["organization_id"],
            level=row["level"],
            total_missions_completed=row["total_missions_completed"],
            total_concepts_mastered=row["total_concepts_mastered"],
            unlocked_areas=unlocked if unlocked else [],
            level_up_at=row["level_up_at"],
            created_at=row["created_at"],
        )
