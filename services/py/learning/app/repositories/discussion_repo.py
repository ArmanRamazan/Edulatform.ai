from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.discussion import Comment, ThreadedComment

_COMMENT_COLUMNS = "id, lesson_id, course_id, user_id, content, parent_id, upvote_count, created_at, updated_at, is_pinned, is_teacher_answer"


class DiscussionRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_comment(
        self,
        lesson_id: UUID,
        course_id: UUID,
        user_id: UUID,
        content: str,
        parent_id: UUID | None,
    ) -> Comment:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO comments (lesson_id, course_id, user_id, content, parent_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING {_COMMENT_COLUMNS}
            """,
            lesson_id, course_id, user_id, content, parent_id,
        )
        return self._to_comment(row)

    async def get_comment_by_id(self, comment_id: UUID) -> Comment | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COMMENT_COLUMNS} FROM comments WHERE id = $1",
            comment_id,
        )
        return self._to_comment(row) if row else None

    async def list_comments(
        self, lesson_id: UUID, limit: int, offset: int,
    ) -> tuple[list[Comment], int]:
        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT count(*) FROM comments WHERE lesson_id = $1",
                lesson_id,
            )
            rows = await conn.fetch(
                f"""
                SELECT {_COMMENT_COLUMNS} FROM comments
                WHERE lesson_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                lesson_id, limit, offset,
            )
        return [self._to_comment(row) for row in rows], total

    async def update_comment(self, comment_id: UUID, content: str) -> Comment | None:
        row = await self._pool.fetchrow(
            f"""
            UPDATE comments
            SET content = $2, updated_at = now()
            WHERE id = $1
            RETURNING {_COMMENT_COLUMNS}
            """,
            comment_id, content,
        )
        return self._to_comment(row) if row else None

    async def delete_comment(self, comment_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM comments WHERE id = $1", comment_id,
        )
        return result == "DELETE 1"

    async def add_vote(self, comment_id: UUID, user_id: UUID) -> bool:
        try:
            await self._pool.execute(
                "INSERT INTO comment_votes (comment_id, user_id) VALUES ($1, $2)",
                comment_id, user_id,
            )
            await self._pool.execute(
                "UPDATE comments SET upvote_count = upvote_count + 1 WHERE id = $1",
                comment_id,
            )
            return True
        except asyncpg.UniqueViolationError:
            return False

    async def remove_vote(self, comment_id: UUID, user_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM comment_votes WHERE comment_id = $1 AND user_id = $2",
            comment_id, user_id,
        )
        if result == "DELETE 1":
            await self._pool.execute(
                "UPDATE comments SET upvote_count = upvote_count - 1 WHERE id = $1",
                comment_id,
            )
            return True
        return False

    async def has_voted(self, comment_id: UUID, user_id: UUID) -> bool:
        count = await self._pool.fetchval(
            "SELECT count(*) FROM comment_votes WHERE comment_id = $1 AND user_id = $2",
            comment_id, user_id,
        )
        return count > 0

    async def set_pinned(
        self, comment_id: UUID, is_pinned: bool,
    ) -> Comment | None:
        row = await self._pool.fetchrow(
            f"""
            UPDATE comments
            SET is_pinned = $2, updated_at = now()
            WHERE id = $1
            RETURNING {_COMMENT_COLUMNS}
            """,
            comment_id, is_pinned,
        )
        return self._to_comment(row) if row else None

    async def set_teacher_answer(
        self, comment_id: UUID, is_teacher_answer: bool,
    ) -> Comment | None:
        row = await self._pool.fetchrow(
            f"""
            UPDATE comments
            SET is_teacher_answer = $2, updated_at = now()
            WHERE id = $1
            RETURNING {_COMMENT_COLUMNS}
            """,
            comment_id, is_teacher_answer,
        )
        return self._to_comment(row) if row else None

    async def get_threaded_comments(
        self, lesson_id: UUID, limit: int, offset: int,
    ) -> tuple[list[ThreadedComment], int]:
        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT count(*) FROM comments WHERE lesson_id = $1 AND parent_id IS NULL",
                lesson_id,
            )
            parent_rows = await conn.fetch(
                f"""
                SELECT {_COMMENT_COLUMNS} FROM comments
                WHERE lesson_id = $1 AND parent_id IS NULL
                ORDER BY is_pinned DESC, is_teacher_answer DESC, created_at DESC
                LIMIT $2 OFFSET $3
                """,
                lesson_id, limit, offset,
            )
            parent_ids = [row["id"] for row in parent_rows]
            if parent_ids:
                reply_rows = await conn.fetch(
                    f"""
                    SELECT {_COMMENT_COLUMNS} FROM comments
                    WHERE parent_id = ANY($1)
                    ORDER BY created_at ASC
                    """,
                    parent_ids,
                )
            else:
                reply_rows = []

        replies_by_parent: dict[UUID, list[Comment]] = {}
        for row in reply_rows:
            comment = self._to_comment(row)
            replies_by_parent.setdefault(comment.parent_id, []).append(comment)

        threads = [
            ThreadedComment(
                comment=self._to_comment(row),
                replies=replies_by_parent.get(row["id"], []),
            )
            for row in parent_rows
        ]
        return threads, total

    @staticmethod
    def _to_comment(row: asyncpg.Record) -> Comment:
        return Comment(
            id=row["id"],
            lesson_id=row["lesson_id"],
            course_id=row["course_id"],
            user_id=row["user_id"],
            content=row["content"],
            parent_id=row["parent_id"],
            upvote_count=row["upvote_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_pinned=row["is_pinned"],
            is_teacher_answer=row["is_teacher_answer"],
        )
