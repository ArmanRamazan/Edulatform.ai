from __future__ import annotations

import json
import logging
from datetime import date
from uuid import UUID

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


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
            logger.warning("Cache read failed for %s", key)
            return None

    async def _set(self, key: str, data: str, ttl: int) -> None:
        try:
            await self._redis.set(key, data, ex=ttl)
        except Exception:
            logger.warning("Cache write failed for %s", key)

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
            logger.warning("Failed to get conversation for %s", session_id)
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
            logger.warning("Failed to save conversation for %s", session_id)

    # --- Credit tracking ---

    async def get_credits_used(self, user_id: str) -> int:
        """Get number of tutor chats used today."""
        key = f"ai:credits:{user_id}:{date.today().isoformat()}"
        try:
            val = await self._redis.get(key)
            return int(val) if val else 0
        except Exception:
            logger.warning("Failed to get credits for %s", user_id)
            return 0

    async def increment_credits(self, user_id: str) -> int:
        """Increment daily credit counter. Returns new count."""
        key = f"ai:credits:{user_id}:{date.today().isoformat()}"
        try:
            count = await self._redis.incr(key)
            await self._redis.expire(key, 86400)
            return count
        except Exception:
            logger.warning("Failed to increment credits for %s", user_id)
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
            logger.warning(
                "Failed to save feedback for %s:%d", session_id, message_index
            )
