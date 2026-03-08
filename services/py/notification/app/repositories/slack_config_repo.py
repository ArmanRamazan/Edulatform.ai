from __future__ import annotations

from uuid import UUID

import asyncpg

from common.errors import ConflictError
from app.domain.slack import SlackConfig


class SlackConfigRepository:
    _COLUMNS = ("org_id", "webhook_url", "channel", "created_at")

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> SlackConfig:
        return SlackConfig(
            org_id=row["org_id"],
            webhook_url=row["webhook_url"],
            channel=row["channel"],
            created_at=row["created_at"],
        )

    async def create(self, org_id: UUID, webhook_url: str, channel: str) -> SlackConfig:
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO slack_configs (org_id, webhook_url, channel)
                    VALUES ($1, $2, $3)
                    RETURNING org_id, webhook_url, channel, created_at
                    """,
                    org_id,
                    webhook_url,
                    channel,
                )
                return self._to_entity(row)
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("Slack config already exists for this org") from exc

    async def get_by_org(self, org_id: UUID) -> SlackConfig | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT org_id, webhook_url, channel, created_at FROM slack_configs WHERE org_id = $1",
                org_id,
            )
            return self._to_entity(row) if row else None

    async def list_all(self) -> list[SlackConfig]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT org_id, webhook_url, channel, created_at FROM slack_configs ORDER BY created_at"
            )
            return [self._to_entity(row) for row in rows]

    async def delete(self, org_id: UUID) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM slack_configs WHERE org_id = $1",
                org_id,
            )
            return result == "DELETE 1"
