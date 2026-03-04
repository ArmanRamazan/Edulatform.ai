from __future__ import annotations

from uuid import UUID

import asyncpg

from common.errors import ConflictError
from app.domain.enrollment import Enrollment, EnrollmentStatus

_COLUMNS = "id, student_id, course_id, payment_id, status, enrolled_at, total_lessons"


class EnrollmentRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        student_id: UUID,
        course_id: UUID,
        payment_id: UUID | None,
        total_lessons: int = 0,
    ) -> Enrollment:
        try:
            row = await self._pool.fetchrow(
                f"""
                INSERT INTO enrollments (student_id, course_id, payment_id, total_lessons)
                VALUES ($1, $2, $3, $4)
                RETURNING {_COLUMNS}
                """,
                student_id,
                course_id,
                payment_id,
                total_lessons,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("Already enrolled in this course") from exc
        return self._to_entity(row)

    async def get_by_student_and_course(
        self, student_id: UUID, course_id: UUID
    ) -> Enrollment | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM enrollments WHERE student_id = $1 AND course_id = $2",
            student_id,
            course_id,
        )
        return self._to_entity(row) if row else None

    async def list_by_student(
        self, student_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Enrollment], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT {_COLUMNS}
                FROM enrollments WHERE student_id = $1
                ORDER BY enrolled_at DESC LIMIT $2 OFFSET $3
                """,
                student_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM enrollments WHERE student_id = $1",
                student_id,
            )
        return [self._to_entity(r) for r in rows], count

    async def count_by_course(self, course_id: UUID) -> int:
        count = await self._pool.fetchval(
            "SELECT count(*) FROM enrollments WHERE course_id = $1",
            course_id,
        )
        return count

    async def update_status(self, enrollment_id: UUID, status: EnrollmentStatus) -> None:
        await self._pool.execute(
            "UPDATE enrollments SET status = $1 WHERE id = $2",
            status,
            enrollment_id,
        )

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Enrollment:
        return Enrollment(
            id=row["id"],
            student_id=row["student_id"],
            course_id=row["course_id"],
            payment_id=row["payment_id"],
            status=EnrollmentStatus(row["status"]),
            enrolled_at=row["enrolled_at"],
            total_lessons=row["total_lessons"],
        )
