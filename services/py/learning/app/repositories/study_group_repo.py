from __future__ import annotations

from uuid import UUID

import asyncpg

from common.errors import ConflictError
from app.domain.study_group import GroupMember, StudyGroup, StudyGroupWithCount

_GROUP_COLUMNS = "id, course_id, name, description, creator_id, max_members, created_at"
_MEMBER_COLUMNS = "id, group_id, user_id, joined_at"


class StudyGroupRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_group(
        self,
        course_id: UUID,
        name: str,
        description: str | None,
        creator_id: UUID,
        max_members: int,
    ) -> StudyGroup:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO study_groups (course_id, name, description, creator_id, max_members)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING {_GROUP_COLUMNS}
            """,
            course_id, name, description, creator_id, max_members,
        )
        return self._to_group(row)

    async def get_group(self, group_id: UUID) -> StudyGroup | None:
        row = await self._pool.fetchrow(
            f"SELECT {_GROUP_COLUMNS} FROM study_groups WHERE id = $1",
            group_id,
        )
        return self._to_group(row) if row else None

    async def get_course_groups(
        self, course_id: UUID, limit: int, offset: int,
    ) -> tuple[list[StudyGroupWithCount], int]:
        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT count(*) FROM study_groups WHERE course_id = $1",
                course_id,
            )
            rows = await conn.fetch(
                f"""
                SELECT sg.{_GROUP_COLUMNS.replace(', ', ', sg.')},
                       (SELECT count(*) FROM study_group_members WHERE group_id = sg.id) AS member_count
                FROM study_groups sg
                WHERE sg.course_id = $1
                ORDER BY sg.created_at DESC
                LIMIT $2 OFFSET $3
                """,
                course_id, limit, offset,
            )
        return [
            StudyGroupWithCount(group=self._to_group(row), member_count=row["member_count"])
            for row in rows
        ], total

    async def get_user_groups(self, user_id: UUID) -> list[StudyGroup]:
        rows = await self._pool.fetch(
            f"""
            SELECT sg.{_GROUP_COLUMNS.replace(', ', ', sg.')}
            FROM study_groups sg
            JOIN study_group_members sgm ON sgm.group_id = sg.id
            WHERE sgm.user_id = $1
            ORDER BY sgm.joined_at DESC
            """,
            user_id,
        )
        return [self._to_group(row) for row in rows]

    async def add_member(self, group_id: UUID, user_id: UUID) -> GroupMember:
        try:
            row = await self._pool.fetchrow(
                f"""
                INSERT INTO study_group_members (group_id, user_id)
                VALUES ($1, $2)
                RETURNING {_MEMBER_COLUMNS}
                """,
                group_id, user_id,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("Already a member of this group") from exc
        return self._to_member(row)

    async def remove_member(self, group_id: UUID, user_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM study_group_members WHERE group_id = $1 AND user_id = $2",
            group_id, user_id,
        )
        return result == "DELETE 1"

    async def get_members(
        self, group_id: UUID, limit: int, offset: int,
    ) -> tuple[list[GroupMember], int]:
        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT count(*) FROM study_group_members WHERE group_id = $1",
                group_id,
            )
            rows = await conn.fetch(
                f"""
                SELECT {_MEMBER_COLUMNS} FROM study_group_members
                WHERE group_id = $1
                ORDER BY joined_at ASC
                LIMIT $2 OFFSET $3
                """,
                group_id, limit, offset,
            )
        return [self._to_member(row) for row in rows], total

    async def count_members(self, group_id: UUID) -> int:
        count = await self._pool.fetchval(
            "SELECT count(*) FROM study_group_members WHERE group_id = $1",
            group_id,
        )
        return count

    async def is_member(self, group_id: UUID, user_id: UUID) -> bool:
        count = await self._pool.fetchval(
            "SELECT count(*) FROM study_group_members WHERE group_id = $1 AND user_id = $2",
            group_id, user_id,
        )
        return count > 0

    @staticmethod
    def _to_group(row: asyncpg.Record) -> StudyGroup:
        return StudyGroup(
            id=row["id"],
            course_id=row["course_id"],
            name=row["name"],
            description=row["description"],
            creator_id=row["creator_id"],
            max_members=row["max_members"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_member(row: asyncpg.Record) -> GroupMember:
        return GroupMember(
            id=row["id"],
            group_id=row["group_id"],
            user_id=row["user_id"],
            joined_at=row["joined_at"],
        )
