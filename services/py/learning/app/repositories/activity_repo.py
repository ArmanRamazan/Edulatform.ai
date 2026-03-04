from __future__ import annotations

import json
from uuid import UUID

import asyncpg

from app.domain.activity import Activity

_COLUMNS = "id, user_id, activity_type, payload, created_at"


class ActivityRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record_activity(
        self, user_id: UUID, activity_type: str, payload: dict,
    ) -> Activity:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO activity_feed (user_id, activity_type, payload)
            VALUES ($1, $2, $3::jsonb)
            RETURNING {_COLUMNS}
            """,
            user_id, activity_type, json.dumps(payload),
        )
        return self._to_activity(row)

    async def get_user_activities(
        self, user_id: UUID, limit: int, offset: int,
    ) -> list[Activity]:
        rows = await self._pool.fetch(
            f"""
            SELECT {_COLUMNS} FROM activity_feed
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id, limit, offset,
        )
        return [self._to_activity(row) for row in rows]

    async def get_feed_for_users(
        self, user_ids: list[UUID], limit: int, offset: int,
    ) -> list[Activity]:
        rows = await self._pool.fetch(
            f"""
            SELECT {_COLUMNS} FROM activity_feed
            WHERE user_id = ANY($1::uuid[])
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_ids, limit, offset,
        )
        return [self._to_activity(row) for row in rows]

    @staticmethod
    def _to_activity(row: asyncpg.Record) -> Activity:
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return Activity(
            id=row["id"],
            user_id=row["user_id"],
            activity_type=row["activity_type"],
            payload=payload,
            created_at=row["created_at"],
        )
