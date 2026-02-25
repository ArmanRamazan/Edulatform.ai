from __future__ import annotations

import json
from uuid import UUID

import asyncpg

from app.domain.quiz import Quiz, Question, QuizAttempt

_QUIZ_COLUMNS = "id, lesson_id, course_id, teacher_id, created_at"
_QUESTION_COLUMNS = 'id, quiz_id, text, options, correct_index, explanation, "order"'
_ATTEMPT_COLUMNS = "id, quiz_id, student_id, answers, score, completed_at"


class QuizRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_quiz(self, lesson_id: UUID, course_id: UUID, teacher_id: UUID) -> Quiz:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO quizzes (lesson_id, course_id, teacher_id)
            VALUES ($1, $2, $3)
            RETURNING {_QUIZ_COLUMNS}
            """,
            lesson_id, course_id, teacher_id,
        )
        return self._to_quiz(row)

    async def create_questions(
        self, quiz_id: UUID, questions: list[tuple[str, list[str], int, str | None, int]]
    ) -> list[Question]:
        rows = []
        for text, options, correct_index, explanation, order in questions:
            row = await self._pool.fetchrow(
                f"""
                INSERT INTO questions (quiz_id, text, options, correct_index, explanation, "order")
                VALUES ($1, $2, $3::jsonb, $4, $5, $6)
                RETURNING {_QUESTION_COLUMNS}
                """,
                quiz_id, text, json.dumps(options), correct_index, explanation, order,
            )
            rows.append(row)
        return [self._to_question(r) for r in rows]

    async def get_quiz_by_lesson(self, lesson_id: UUID) -> Quiz | None:
        row = await self._pool.fetchrow(
            f"SELECT {_QUIZ_COLUMNS} FROM quizzes WHERE lesson_id = $1",
            lesson_id,
        )
        return self._to_quiz(row) if row else None

    async def get_quiz_by_id(self, quiz_id: UUID) -> Quiz | None:
        row = await self._pool.fetchrow(
            f"SELECT {_QUIZ_COLUMNS} FROM quizzes WHERE id = $1",
            quiz_id,
        )
        return self._to_quiz(row) if row else None

    async def get_questions(self, quiz_id: UUID) -> list[Question]:
        rows = await self._pool.fetch(
            f'SELECT {_QUESTION_COLUMNS} FROM questions WHERE quiz_id = $1 ORDER BY "order"',
            quiz_id,
        )
        return [self._to_question(r) for r in rows]

    async def create_attempt(
        self, quiz_id: UUID, student_id: UUID, answers: list[int], score: float
    ) -> QuizAttempt:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO quiz_attempts (quiz_id, student_id, answers, score)
            VALUES ($1, $2, $3::jsonb, $4)
            RETURNING {_ATTEMPT_COLUMNS}
            """,
            quiz_id, student_id, json.dumps(answers), score,
        )
        return self._to_attempt(row)

    async def list_attempts(
        self, quiz_id: UUID, student_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[QuizAttempt], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT {_ATTEMPT_COLUMNS} FROM quiz_attempts
                WHERE quiz_id = $1 AND student_id = $2
                ORDER BY completed_at DESC LIMIT $3 OFFSET $4
                """,
                quiz_id, student_id, limit, offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM quiz_attempts WHERE quiz_id = $1 AND student_id = $2",
                quiz_id, student_id,
            )
        return [self._to_attempt(r) for r in rows], count

    @staticmethod
    def _to_quiz(row: asyncpg.Record) -> Quiz:
        return Quiz(
            id=row["id"],
            lesson_id=row["lesson_id"],
            course_id=row["course_id"],
            teacher_id=row["teacher_id"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_question(row: asyncpg.Record) -> Question:
        options = row["options"]
        if isinstance(options, str):
            options = json.loads(options)
        return Question(
            id=row["id"],
            quiz_id=row["quiz_id"],
            text=row["text"],
            options=options,
            correct_index=row["correct_index"],
            explanation=row["explanation"],
            order=row["order"],
        )

    @staticmethod
    def _to_attempt(row: asyncpg.Record) -> QuizAttempt:
        answers = row["answers"]
        if isinstance(answers, str):
            answers = json.loads(answers)
        return QuizAttempt(
            id=row["id"],
            quiz_id=row["quiz_id"],
            student_id=row["student_id"],
            answers=answers,
            score=row["score"],
            completed_at=row["completed_at"],
        )
