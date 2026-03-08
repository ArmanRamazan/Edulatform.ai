from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.notification import Notification, NotificationType


class NotificationRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        user_id: UUID,
        type: NotificationType,
        title: str,
        body: str,
        email_sent: bool = False,
        organization_id: UUID | None = None,
        event_id: str | None = None,
    ) -> Notification:
        row = await self._pool.fetchrow(
            """
            INSERT INTO notifications (user_id, type, title, body, email_sent, organization_id, event_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, user_id, type, title, body, is_read, created_at, email_sent, organization_id, event_id
            """,
            user_id,
            type,
            title,
            body,
            email_sent,
            organization_id,
            event_id,
        )
        return self._to_entity(row)

    async def exists_by_event_id(self, event_id: str) -> bool:
        count = await self._pool.fetchval(
            "SELECT count(*) FROM notifications WHERE event_id = $1",
            event_id,
        )
        return count > 0

    async def list_by_user(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Notification], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, type, title, body, is_read, created_at, email_sent, organization_id
                FROM notifications WHERE user_id = $1
                ORDER BY created_at DESC LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM notifications WHERE user_id = $1",
                user_id,
            )
        return [self._to_entity(r) for r in rows], count

    async def list_by_org(
        self, organization_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Notification], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, type, title, body, is_read, created_at, email_sent, organization_id
                FROM notifications WHERE organization_id = $1
                ORDER BY created_at DESC LIMIT $2 OFFSET $3
                """,
                organization_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM notifications WHERE organization_id = $1",
                organization_id,
            )
        return [self._to_entity(r) for r in rows], count

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, user_id, type, title, body, is_read, created_at, email_sent, organization_id
            FROM notifications WHERE id = $1
            """,
            notification_id,
        )
        return self._to_entity(row) if row else None

    async def has_unread_by_type(
        self, user_id: UUID, type: NotificationType,
    ) -> bool:
        count = await self._pool.fetchval(
            """
            SELECT count(*) FROM notifications
            WHERE user_id = $1 AND type = $2 AND is_read = false
            """,
            user_id,
            type,
        )
        return count > 0

    async def get_distinct_user_ids(self) -> list[UUID]:
        rows = await self._pool.fetch(
            "SELECT DISTINCT user_id FROM notifications"
        )
        return [row["user_id"] for row in rows]

    async def mark_as_read(self, notification_id: UUID) -> Notification | None:
        row = await self._pool.fetchrow(
            """
            UPDATE notifications SET is_read = true WHERE id = $1
            RETURNING id, user_id, type, title, body, is_read, created_at, email_sent, organization_id
            """,
            notification_id,
        )
        return self._to_entity(row) if row else None

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Notification:
        return Notification(
            id=row["id"],
            user_id=row["user_id"],
            type=NotificationType(row["type"]),
            title=row["title"],
            body=row["body"],
            is_read=row["is_read"],
            created_at=row["created_at"],
            email_sent=row.get("email_sent", False),
            organization_id=row.get("organization_id"),
            event_id=row.get("event_id"),
        )
