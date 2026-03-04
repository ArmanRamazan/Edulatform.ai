from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.messaging import Message


class MessageRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_message(
        self, conversation_id: UUID, sender_id: UUID, content: str,
    ) -> Message:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO messages (conversation_id, sender_id, content)
                VALUES ($1, $2, $3)
                RETURNING id, conversation_id, sender_id, content, is_read, created_at
                """,
                conversation_id,
                sender_id,
                content,
            )
            await conn.execute(
                """
                UPDATE conversations SET last_message_at = now()
                WHERE id = $1
                """,
                conversation_id,
            )
        return self._to_entity(row)

    async def get_messages(
        self, conversation_id: UUID, limit: int = 50, offset: int = 0,
    ) -> tuple[list[Message], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, conversation_id, sender_id, content, is_read, created_at
                FROM messages WHERE conversation_id = $1
                ORDER BY created_at DESC LIMIT $2 OFFSET $3
                """,
                conversation_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM messages WHERE conversation_id = $1",
                conversation_id,
            )
        return [self._to_entity(r) for r in rows], count

    async def get_by_id(self, message_id: UUID) -> Message | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, conversation_id, sender_id, content, is_read, created_at
            FROM messages WHERE id = $1
            """,
            message_id,
        )
        return self._to_entity(row) if row else None

    async def mark_as_read(self, message_id: UUID, user_id: UUID) -> bool:
        result = await self._pool.execute(
            """
            UPDATE messages SET is_read = true
            WHERE id = $1 AND sender_id != $2
            """,
            message_id,
            user_id,
        )
        return result == "UPDATE 1"

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Message:
        return Message(
            id=row["id"],
            conversation_id=row["conversation_id"],
            sender_id=row["sender_id"],
            content=row["content"],
            is_read=row["is_read"],
            created_at=row["created_at"],
        )
