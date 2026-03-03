from __future__ import annotations

from uuid import UUID

import asyncpg


class VelocityRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_concepts_mastered_by_week(
        self, user_id: UUID, weeks: int = 4,
    ) -> list[dict]:
        rows = await self._pool.fetch(
            """
            SELECT date_trunc('week', cm.updated_at)::date::text AS week_start,
                   COUNT(*) AS count
            FROM concept_mastery cm
            WHERE cm.student_id = $1
              AND cm.mastery >= 0.7
              AND cm.updated_at >= now() - make_interval(weeks => $2)
            GROUP BY date_trunc('week', cm.updated_at)
            ORDER BY week_start
            """,
            user_id, weeks,
        )
        return [{"week_start": r["week_start"], "count": r["count"]} for r in rows]

    async def get_quiz_score_trend(
        self, user_id: UUID, weeks: int = 4,
    ) -> list[dict]:
        rows = await self._pool.fetch(
            """
            SELECT date_trunc('week', qa.completed_at)::date::text AS week_start,
                   ROUND(AVG(qa.score)::numeric, 2) AS avg_score
            FROM quiz_attempts qa
            WHERE qa.student_id = $1
              AND qa.completed_at >= now() - make_interval(weeks => $2)
            GROUP BY date_trunc('week', qa.completed_at)
            ORDER BY week_start
            """,
            user_id, weeks,
        )
        return [
            {"week_start": r["week_start"], "avg_score": float(r["avg_score"])}
            for r in rows
        ]

    async def get_flashcard_retention_rate(self, user_id: UUID) -> float:
        row = await self._pool.fetchrow(
            """
            SELECT COUNT(*) FILTER (WHERE rl.rating >= 3) AS correct,
                   COUNT(*) AS total
            FROM review_logs rl
            JOIN flashcards f ON f.id = rl.card_id
            WHERE f.student_id = $1
              AND rl.reviewed_at >= now() - interval '30 days'
            """,
            user_id,
        )
        if not row or row["total"] == 0:
            return 0.0
        return round(row["correct"] / row["total"], 2)

    async def get_learning_streak(self, user_id: UUID) -> int:
        row = await self._pool.fetchrow(
            "SELECT current_streak FROM streaks WHERE user_id = $1",
            user_id,
        )
        return row["current_streak"] if row else 0

    async def get_course_progress(self, user_id: UUID) -> list[dict]:
        rows = await self._pool.fetch(
            """
            SELECT c.course_id,
                   COUNT(*) AS total_concepts,
                   COUNT(*) FILTER (
                       WHERE cm.mastery >= 0.7
                   ) AS mastered
            FROM concepts c
            LEFT JOIN concept_mastery cm
                ON cm.concept_id = c.id AND cm.student_id = $1
            WHERE c.course_id IN (
                SELECT DISTINCT c2.course_id
                FROM concept_mastery cm2
                JOIN concepts c2 ON c2.id = cm2.concept_id
                WHERE cm2.student_id = $1
            )
            GROUP BY c.course_id
            ORDER BY c.course_id
            """,
            user_id,
        )
        return [
            {
                "course_id": str(r["course_id"]),
                "total_concepts": r["total_concepts"],
                "mastered": r["mastered"],
            }
            for r in rows
        ]
