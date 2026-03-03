from __future__ import annotations

import json
from datetime import date
from uuid import UUID

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger()


class AICache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get_quiz(self, lesson_id: UUID) -> str | None:
        return await self._get(f"ai:quiz:{lesson_id}")

    async def set_quiz(self, lesson_id: UUID, data: str, ttl: int) -> None:
        await self._set(f"ai:quiz:{lesson_id}", data, ttl)

    async def get_summary(self, lesson_id: UUID) -> str | None:
        return await self._get(f"ai:summary:{lesson_id}")

    async def set_summary(self, lesson_id: UUID, data: str, ttl: int) -> None:
        await self._set(f"ai:summary:{lesson_id}", data, ttl)

    async def _get(self, key: str) -> str | None:
        try:
            val = await self._redis.get(key)
            return val.decode() if isinstance(val, bytes) else val
        except Exception:
            logger.warning("cache_read_failed", key=key)
            return None

    async def _set(self, key: str, data: str, ttl: int) -> None:
        try:
            await self._redis.set(key, data, ex=ttl)
        except Exception:
            logger.warning("cache_write_failed", key=key)

    # --- Tutor conversation memory ---

    async def get_conversation(self, session_id: str) -> list[dict]:
        """Get conversation history for a session."""
        try:
            val = await self._redis.get(f"ai:tutor:session:{session_id}")
            if val is None:
                return []
            raw = val.decode() if isinstance(val, bytes) else val
            return json.loads(raw)
        except Exception:
            logger.warning("conversation_get_failed", session_id=session_id)
            return []

    async def save_conversation(
        self, session_id: str, messages: list[dict], ttl: int
    ) -> None:
        """Save conversation history for a session."""
        try:
            await self._redis.set(
                f"ai:tutor:session:{session_id}",
                json.dumps(messages),
                ex=ttl,
            )
        except Exception:
            logger.warning("conversation_save_failed", session_id=session_id)

    # --- Credit tracking ---

    async def get_credits_used(self, user_id: str) -> int:
        """Get number of tutor chats used today."""
        key = f"ai:credits:{user_id}:{date.today().isoformat()}"
        try:
            val = await self._redis.get(key)
            return int(val) if val else 0
        except Exception:
            logger.warning("credits_get_failed", user_id=user_id)
            return 0

    async def increment_credits(self, user_id: str) -> int:
        """Increment daily credit counter. Returns new count."""
        key = f"ai:credits:{user_id}:{date.today().isoformat()}"
        try:
            count = await self._redis.incr(key)
            await self._redis.expire(key, 86400)
            return count
        except Exception:
            logger.warning("credits_increment_failed", user_id=user_id)
            return 0

    # --- Tutor feedback ---

    async def save_feedback(
        self, session_id: str, message_index: int, rating: int
    ) -> None:
        """Save feedback for a specific tutor message."""
        key = f"ai:tutor:feedback:{session_id}:{message_index}"
        try:
            await self._redis.set(key, str(rating), ex=86400)
        except Exception:
            logger.warning("feedback_save_failed", session_id=session_id, message_index=message_index)
