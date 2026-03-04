from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import asyncpg

from app.domain.bundle import BundleWithCourses, CourseBundle, BundleCourse
from app.domain.course import Course, CourseLevel

_BUNDLE_COLUMNS = "id, teacher_id, title, description, price, discount_percent, is_active, created_at"

_ALLOWED_UPDATE_COLUMNS = frozenset({
    "title", "description", "price", "discount_percent", "is_active",
})


class BundleRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_bundle_with_courses(
        self,
        teacher_id: UUID,
        title: str,
        description: str,
        price: Decimal,
        discount_percent: int,
        course_ids: list[UUID],
    ) -> BundleWithCourses:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    f"""
                    INSERT INTO course_bundles (teacher_id, title, description, price, discount_percent)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING {_BUNDLE_COLUMNS}
                    """,
                    teacher_id, title, description, price, discount_percent,
                )
                bundle = self._to_bundle(row)
                for course_id in course_ids:
                    await conn.execute(
                        "INSERT INTO bundle_courses (bundle_id, course_id) VALUES ($1, $2)",
                        bundle.id, course_id,
                    )
                courses = await self._fetch_courses(conn, bundle.id)
        return BundleWithCourses(bundle=bundle, courses=courses)

    async def get_bundle(self, bundle_id: UUID) -> CourseBundle | None:
        row = await self._pool.fetchrow(
            f"SELECT {_BUNDLE_COLUMNS} FROM course_bundles WHERE id = $1",
            bundle_id,
        )
        return self._to_bundle(row) if row else None

    async def get_bundle_with_courses(self, bundle_id: UUID) -> BundleWithCourses | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_BUNDLE_COLUMNS} FROM course_bundles WHERE id = $1",
                bundle_id,
            )
            if not row:
                return None
            bundle = self._to_bundle(row)
            courses = await self._fetch_courses(conn, bundle_id)
        return BundleWithCourses(bundle=bundle, courses=courses)

    async def list_bundles(
        self, limit: int = 20, offset: int = 0, teacher_id: UUID | None = None,
    ) -> tuple[list[CourseBundle], int]:
        if teacher_id:
            rows = await self._pool.fetch(
                f"""SELECT {_BUNDLE_COLUMNS} FROM course_bundles
                    WHERE teacher_id = $1 AND is_active = true
                    ORDER BY created_at DESC LIMIT $2 OFFSET $3""",
                teacher_id, limit, offset,
            )
            count = await self._pool.fetchval(
                "SELECT count(*) FROM course_bundles WHERE teacher_id = $1 AND is_active = true",
                teacher_id,
            )
        else:
            rows = await self._pool.fetch(
                f"""SELECT {_BUNDLE_COLUMNS} FROM course_bundles
                    WHERE is_active = true
                    ORDER BY created_at DESC LIMIT $1 OFFSET $2""",
                limit, offset,
            )
            count = await self._pool.fetchval(
                "SELECT count(*) FROM course_bundles WHERE is_active = true",
            )
        return [self._to_bundle(r) for r in rows], count

    async def update_bundle(self, bundle_id: UUID, **fields: object) -> CourseBundle | None:
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
            return await self.get_bundle(bundle_id)
        values.append(bundle_id)
        row = await self._pool.fetchrow(
            f"UPDATE course_bundles SET {', '.join(sets)} WHERE id = ${idx} RETURNING {_BUNDLE_COLUMNS}",
            *values,
        )
        return self._to_bundle(row) if row else None

    async def delete_bundle(self, bundle_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM course_bundles WHERE id = $1", bundle_id,
        )
        return result == "DELETE 1"

    async def _fetch_courses(self, conn: asyncpg.Connection, bundle_id: UUID) -> list[Course]:
        rows = await conn.fetch(
            """SELECT c.id, c.teacher_id, c.title, c.description, c.is_free, c.price,
                      c.duration_minutes, c.level, c.created_at,
                      c.avg_rating, c.review_count, c.category_id
               FROM courses c
               JOIN bundle_courses bc ON bc.course_id = c.id
               WHERE bc.bundle_id = $1
               ORDER BY c.created_at""",
            bundle_id,
        )
        return [self._to_course(r) for r in rows]

    @staticmethod
    def _to_bundle(row: asyncpg.Record) -> CourseBundle:
        return CourseBundle(
            id=row["id"],
            teacher_id=row["teacher_id"],
            title=row["title"],
            description=row["description"],
            price=row["price"],
            discount_percent=row["discount_percent"],
            is_active=row["is_active"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_course(row: asyncpg.Record) -> Course:
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
