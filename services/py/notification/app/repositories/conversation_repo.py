from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.messaging import Conversation, ConversationPreview


class ConversationRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_or_create(self, user_id_1: UUID, user_id_2: UUID) -> Conversation:
        p1, p2 = sorted([user_id_1, user_id_2])
        row = await self._pool.fetchrow(
            """
            INSERT INTO conversations (participant_1, participant_2)
            VALUES ($1, $2)
            ON CONFLICT (participant_1, participant_2) DO UPDATE
                SET participant_1 = conversations.participant_1
            RETURNING id, participant_1, participant_2, created_at, last_message_at
            """,
            p1,
            p2,
        )
        return self._to_entity(row)

    async def get_user_conversations(
        self, user_id: UUID, limit: int = 20, offset: int = 0,
    ) -> tuple[list[ConversationPreview], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    c.id AS conversation_id,
                    CASE WHEN c.participant_1 = $1 THEN c.participant_2
                         ELSE c.participant_1 END AS other_user_id,
                    COALESCE(
                        (SELECT content FROM messages
                         WHERE conversation_id = c.id
                         ORDER BY created_at DESC LIMIT 1),
                        ''
                    ) AS last_message_content,
                    c.last_message_at,
                    (SELECT count(*) FROM messages
                     WHERE conversation_id = c.id
                       AND sender_id != $1
                       AND is_read = false
                    ) AS unread_count
                FROM conversations c
                WHERE c.participant_1 = $1 OR c.participant_2 = $1
                ORDER BY c.last_message_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                """
                SELECT count(*) FROM conversations
                WHERE participant_1 = $1 OR participant_2 = $1
                """,
                user_id,
            )
        return [self._to_preview(r) for r in rows], count

    async def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, participant_1, participant_2, created_at, last_message_at
            FROM conversations WHERE id = $1
            """,
            conversation_id,
        )
        return self._to_entity(row) if row else None

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Conversation:
        return Conversation(
            id=row["id"],
            participant_1=row["participant_1"],
            participant_2=row["participant_2"],
            created_at=row["created_at"],
            last_message_at=row["last_message_at"],
        )

    @staticmethod
    def _to_preview(row: asyncpg.Record) -> ConversationPreview:
        return ConversationPreview(
            conversation_id=row["conversation_id"],
            other_user_id=row["other_user_id"],
            last_message_content=row["last_message_content"],
            last_message_at=row["last_message_at"],
            unread_count=row["unread_count"],
        )
