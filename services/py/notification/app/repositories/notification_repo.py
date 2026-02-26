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
    ) -> Notification:
        row = await self._pool.fetchrow(
            """
            INSERT INTO notifications (user_id, type, title, body)
            VALUES ($1, $2, $3, $4)
            RETURNING id, user_id, type, title, body, is_read, created_at
            """,
            user_id,
            type,
            title,
            body,
        )
        return self._to_entity(row)

    async def list_by_user(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Notification], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, type, title, body, is_read, created_at
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

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, user_id, type, title, body, is_read, created_at
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

    async def mark_as_read(self, notification_id: UUID) -> Notification | None:
        row = await self._pool.fetchrow(
            """
            UPDATE notifications SET is_read = true WHERE id = $1
            RETURNING id, user_id, type, title, body, is_read, created_at
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
        )
