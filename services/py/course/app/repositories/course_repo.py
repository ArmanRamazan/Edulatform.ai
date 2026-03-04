from __future__ import annotations

import base64
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.domain.course import Course, CourseLevel

_COLUMNS = "id, teacher_id, title, description, is_free, price, duration_minutes, level, created_at, avg_rating, review_count, category_id"

_ALLOWED_UPDATE_COLUMNS = frozenset({
    "title", "description", "is_free", "price", "duration_minutes", "level", "category_id",
})


def _encode_cursor(created_at: datetime, id: UUID) -> str:
    return base64.urlsafe_b64encode(f"{created_at.isoformat()}|{id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts, uid = raw.split("|", 1)
    return datetime.fromisoformat(ts), UUID(uid)


class CourseRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        teacher_id: UUID,
        title: str,
        description: str,
        is_free: bool,
        price: Decimal | None,
        duration_minutes: int,
        level: CourseLevel,
        category_id: UUID | None = None,
    ) -> Course:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO courses (teacher_id, title, description, is_free, price, duration_minutes, level, category_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING {_COLUMNS}
            """,
            teacher_id,
            title,
            description,
            is_free,
            price,
            duration_minutes,
            level,
            category_id,
        )
        return self._to_entity(row)

    async def get_by_id(self, course_id: UUID) -> Course | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM courses WHERE id = $1",
            course_id,
        )
        return self._to_entity(row) if row else None

    async def list(self, limit: int = 20, offset: int = 0) -> tuple[list[Course], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_COLUMNS} FROM courses ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit,
                offset,
            )
            count = await conn.fetchval("SELECT count(*) FROM courses")
        return [self._to_entity(r) for r in rows], count

    async def list_cursor(
        self, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[Course], int, str | None]:
        async with self._pool.acquire() as conn:
            if cursor:
                ts, uid = _decode_cursor(cursor)
                rows = await conn.fetch(
                    f"""SELECT {_COLUMNS} FROM courses
                        WHERE (created_at, id) < ($1, $2)
                        ORDER BY created_at DESC, id DESC
                        LIMIT $3""",
                    ts, uid, limit,
                )
            else:
                rows = await conn.fetch(
                    f"SELECT {_COLUMNS} FROM courses ORDER BY created_at DESC, id DESC LIMIT $1",
                    limit,
                )
            count = await conn.fetchval("SELECT count(*) FROM courses")
        items = [self._to_entity(r) for r in rows]
        next_cur = _encode_cursor(items[-1].created_at, items[-1].id) if len(items) == limit else None
        return items, count, next_cur

    async def search(self, query: str, limit: int = 20, offset: int = 0) -> tuple[list[Course], int]:
        """Search courses by title/description using ILIKE (accelerated by pg_trgm GIN index)."""
        async with self._pool.acquire() as conn:
            pattern = f"%{query}%"
            rows = await conn.fetch(
                f"""
                SELECT {_COLUMNS} FROM courses
                WHERE title ILIKE $1 OR description ILIKE $1
                ORDER BY created_at DESC LIMIT $2 OFFSET $3
                """,
                pattern,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM courses WHERE title ILIKE $1 OR description ILIKE $1",
                pattern,
            )
        return [self._to_entity(r) for r in rows], count

    async def search_cursor(
        self, query: str, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[Course], int, str | None]:
        async with self._pool.acquire() as conn:
            pattern = f"%{query}%"
            if cursor:
                ts, uid = _decode_cursor(cursor)
                rows = await conn.fetch(
                    f"""SELECT {_COLUMNS} FROM courses
                        WHERE (title ILIKE $1 OR description ILIKE $1)
                          AND (created_at, id) < ($2, $3)
                        ORDER BY created_at DESC, id DESC
                        LIMIT $4""",
                    pattern, ts, uid, limit,
                )
            else:
                rows = await conn.fetch(
                    f"""SELECT {_COLUMNS} FROM courses
                        WHERE title ILIKE $1 OR description ILIKE $1
                        ORDER BY created_at DESC, id DESC LIMIT $2""",
                    pattern, limit,
                )
            count = await conn.fetchval(
                "SELECT count(*) FROM courses WHERE title ILIKE $1 OR description ILIKE $1",
                pattern,
            )
        items = [self._to_entity(r) for r in rows]
        next_cur = _encode_cursor(items[-1].created_at, items[-1].id) if len(items) == limit else None
        return items, count, next_cur

    async def list_by_teacher(
        self, teacher_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Course], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_COLUMNS} FROM courses WHERE teacher_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                teacher_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM courses WHERE teacher_id = $1",
                teacher_id,
            )
        return [self._to_entity(r) for r in rows], count

    async def list_by_teacher_cursor(
        self, teacher_id: UUID, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[Course], int, str | None]:
        async with self._pool.acquire() as conn:
            if cursor:
                ts, uid = _decode_cursor(cursor)
                rows = await conn.fetch(
                    f"""SELECT {_COLUMNS} FROM courses
                        WHERE teacher_id = $1 AND (created_at, id) < ($2, $3)
                        ORDER BY created_at DESC, id DESC
                        LIMIT $4""",
                    teacher_id, ts, uid, limit,
                )
            else:
                rows = await conn.fetch(
                    f"SELECT {_COLUMNS} FROM courses WHERE teacher_id = $1 ORDER BY created_at DESC, id DESC LIMIT $2",
                    teacher_id, limit,
                )
            count = await conn.fetchval(
                "SELECT count(*) FROM courses WHERE teacher_id = $1",
                teacher_id,
            )
        items = [self._to_entity(r) for r in rows]
        next_cur = _encode_cursor(items[-1].created_at, items[-1].id) if len(items) == limit else None
        return items, count, next_cur

    async def list_filtered(
        self,
        limit: int = 20,
        offset: int = 0,
        category_id: UUID | None = None,
        level: str | None = None,
        is_free: bool | None = None,
        q: str | None = None,
        sort_by: str = "created_at",
    ) -> tuple[list[Course], int]:
        conditions: list[str] = []
        params: list[object] = []
        idx = 1

        if category_id is not None:
            conditions.append(f"category_id = ${idx}")
            params.append(category_id)
            idx += 1

        if level is not None:
            conditions.append(f"level = ${idx}")
            params.append(level)
            idx += 1

        if is_free is not None:
            conditions.append(f"is_free = ${idx}")
            params.append(is_free)
            idx += 1

        if q:
            pattern = f"%{q}%"
            conditions.append(f"(title ILIKE ${idx} OR description ILIKE ${idx})")
            params.append(pattern)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        order_map = {
            "created_at": "created_at DESC",
            "avg_rating": "avg_rating DESC NULLS LAST, created_at DESC",
            "price": "price ASC NULLS LAST, created_at DESC",
        }
        order = order_map.get(sort_by, "created_at DESC")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {_COLUMNS} FROM courses {where} ORDER BY {order} LIMIT ${idx} OFFSET ${idx + 1}",
                *params, limit, offset,
            )
            count = await conn.fetchval(
                f"SELECT count(*) FROM courses {where}",
                *params,
            )
        return [self._to_entity(r) for r in rows], count

    async def update(self, course_id: UUID, **fields: object) -> Course | None:
        sets: list[str] = []
        values: list[object] = []
        idx = 1
        for key, val in fields.items():
            if key not in _ALLOWED_UPDATE_COLUMNS:
                raise ValueError(f"Cannot update column: {key}")
            sets.append(f"{key} = ${idx}")
            values.append(val)
            idx += 1
        if not sets:
            return await self.get_by_id(course_id)
        values.append(course_id)
        row = await self._pool.fetchrow(
            f"UPDATE courses SET {', '.join(sets)} WHERE id = ${idx} RETURNING {_COLUMNS}",
            *values,
        )
        return self._to_entity(row) if row else None

    async def update_rating(
        self, course_id: UUID, avg_rating: Decimal | None, review_count: int
    ) -> None:
        await self._pool.execute(
            "UPDATE courses SET avg_rating = $1, review_count = $2 WHERE id = $3",
            avg_rating,
            review_count,
            course_id,
        )

    async def get_analytics_by_teacher(self, teacher_id: UUID) -> list[dict]:
        rows = await self._pool.fetch(
            """
            SELECT course_id, title, avg_rating, review_count, module_count, lesson_count
            FROM course_analytics
            WHERE teacher_id = $1
            ORDER BY course_id
            """,
            teacher_id,
        )
        return [dict(r) for r in rows]

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Course:
        return Course(
            id=row["id"],
            teacher_id=row["teacher_id"],
            title=row["title"],
            description=row["description"],
            is_free=row["is_free"],
            price=row["price"],
            duration_minutes=row["duration_minutes"],
            level=CourseLevel(row["level"]),
            created_at=row["created_at"],
            avg_rating=row["avg_rating"],
            review_count=row["review_count"],
            category_id=row["category_id"],
        )
