from __future__ import annotations

from uuid import UUID

import asyncpg

from common.errors import ConflictError
from app.domain.follow import Follow

_COLUMNS = "id, follower_id, following_id, created_at"


class FollowRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def follow(self, follower_id: UUID, following_id: UUID) -> Follow:
        try:
            row = await self._pool.fetchrow(
                f"INSERT INTO follows (follower_id, following_id) VALUES ($1, $2) RETURNING {_COLUMNS}",
                follower_id,
                following_id,
            )
        except asyncpg.UniqueViolationError:
            raise ConflictError("Already following this user")
        return self._to_entity(row)

    async def unfollow(self, follower_id: UUID, following_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM follows WHERE follower_id = $1 AND following_id = $2",
            follower_id,
            following_id,
        )
        return result == "DELETE 1"

    async def get_followers(self, user_id: UUID, limit: int, offset: int) -> tuple[list[Follow], int]:
        rows = await self._pool.fetch(
            f"SELECT {_COLUMNS} FROM follows WHERE following_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            user_id,
            limit,
            offset,
        )
        total = await self._pool.fetchval(
            "SELECT COUNT(*) FROM follows WHERE following_id = $1",
            user_id,
        )
        return [self._to_entity(r) for r in rows], total

    async def get_following(self, user_id: UUID, limit: int, offset: int) -> tuple[list[Follow], int]:
        rows = await self._pool.fetch(
            f"SELECT {_COLUMNS} FROM follows WHERE follower_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            user_id,
            limit,
            offset,
        )
        total = await self._pool.fetchval(
            "SELECT COUNT(*) FROM follows WHERE follower_id = $1",
            user_id,
        )
        return [self._to_entity(r) for r in rows], total

    async def is_following(self, follower_id: UUID, following_id: UUID) -> bool:
        val = await self._pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM follows WHERE follower_id = $1 AND following_id = $2)",
            follower_id,
            following_id,
        )
        return val

    async def count_followers(self, user_id: UUID) -> int:
        return await self._pool.fetchval(
            "SELECT COUNT(*) FROM follows WHERE following_id = $1",
            user_id,
        )

    async def count_following(self, user_id: UUID) -> int:
        return await self._pool.fetchval(
            "SELECT COUNT(*) FROM follows WHERE follower_id = $1",
            user_id,
        )

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Follow:
        return Follow(
            id=row["id"],
            follower_id=row["follower_id"],
            following_id=row["following_id"],
            created_at=row["created_at"],
        )
