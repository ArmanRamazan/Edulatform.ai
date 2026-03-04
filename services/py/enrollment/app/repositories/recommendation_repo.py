from __future__ import annotations

from uuid import UUID

import asyncpg


class RecommendationRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_similar_courses(
        self, course_id: UUID, limit: int = 5
    ) -> list[dict]:
        """Find courses frequently co-enrolled with the given course."""
        rows = await self._pool.fetch(
            """
            SELECT e2.course_id, COUNT(*) AS co_enrollment_count
            FROM enrollments e1
            JOIN enrollments e2 ON e1.student_id = e2.student_id
            WHERE e1.course_id = $1 AND e2.course_id != $1
            GROUP BY e2.course_id
            ORDER BY co_enrollment_count DESC
            LIMIT $2
            """,
            course_id,
            limit,
        )
        return [
            {"course_id": row["course_id"], "co_enrollment_count": row["co_enrollment_count"]}
            for row in rows
        ]

    async def get_personalized_recommendations(
        self, user_id: UUID, limit: int = 10
    ) -> list[dict]:
        """Recommend courses popular among users with similar enrollment patterns,
        excluding courses the user is already enrolled in."""
        rows = await self._pool.fetch(
            """
            SELECT e3.course_id, COUNT(*) AS co_enrollment_count
            FROM enrollments e1
            JOIN enrollments e2 ON e1.course_id = e2.course_id AND e1.student_id != e2.student_id
            JOIN enrollments e3 ON e2.student_id = e3.student_id
            WHERE e1.student_id = $1
              AND e3.course_id NOT IN (
                  SELECT course_id FROM enrollments WHERE student_id = $1
              )
            GROUP BY e3.course_id
            ORDER BY co_enrollment_count DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )
        return [
            {"course_id": row["course_id"], "co_enrollment_count": row["co_enrollment_count"]}
            for row in rows
        ]
