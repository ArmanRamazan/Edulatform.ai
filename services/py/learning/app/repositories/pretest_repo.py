from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.pretest import Pretest, PretestAnswer

_PRETEST_COLUMNS = "id, user_id, course_id, started_at, completed_at, status"
_ANSWER_COLUMNS = "id, pretest_id, concept_id, question, user_answer, correct_answer, is_correct, created_at"


class PretestRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_pretest(self, user_id: UUID, course_id: UUID) -> Pretest:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO pretests (user_id, course_id)
            VALUES ($1, $2)
            RETURNING {_PRETEST_COLUMNS}
            """,
            user_id, course_id,
        )
        return self._to_pretest(row)

    async def get_by_user_and_course(
        self, user_id: UUID, course_id: UUID
    ) -> Pretest | None:
        row = await self._pool.fetchrow(
            f"SELECT {_PRETEST_COLUMNS} FROM pretests WHERE user_id = $1 AND course_id = $2",
            user_id, course_id,
        )
        return self._to_pretest(row) if row else None

    async def get_by_id(self, pretest_id: UUID) -> Pretest | None:
        row = await self._pool.fetchrow(
            f"SELECT {_PRETEST_COLUMNS} FROM pretests WHERE id = $1",
            pretest_id,
        )
        return self._to_pretest(row) if row else None

    async def complete_pretest(self, pretest_id: UUID) -> Pretest:
        row = await self._pool.fetchrow(
            f"""
            UPDATE pretests SET status = 'completed', completed_at = now()
            WHERE id = $1
            RETURNING {_PRETEST_COLUMNS}
            """,
            pretest_id,
        )
        return self._to_pretest(row)

    async def add_answer(
        self,
        pretest_id: UUID,
        concept_id: UUID,
        question: str,
        correct_answer: str,
    ) -> PretestAnswer:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO pretest_answers (pretest_id, concept_id, question, correct_answer)
            VALUES ($1, $2, $3, $4)
            RETURNING {_ANSWER_COLUMNS}
            """,
            pretest_id, concept_id, question, correct_answer,
        )
        return self._to_answer(row)

    async def update_answer(
        self, answer_id: UUID, user_answer: str, is_correct: bool
    ) -> PretestAnswer:
        row = await self._pool.fetchrow(
            f"""
            UPDATE pretest_answers SET user_answer = $2, is_correct = $3
            WHERE id = $1
            RETURNING {_ANSWER_COLUMNS}
            """,
            answer_id, user_answer, is_correct,
        )
        return self._to_answer(row)

    async def get_answers(self, pretest_id: UUID) -> list[PretestAnswer]:
        rows = await self._pool.fetch(
            f"SELECT {_ANSWER_COLUMNS} FROM pretest_answers WHERE pretest_id = $1 ORDER BY created_at",
            pretest_id,
        )
        return [self._to_answer(r) for r in rows]

    @staticmethod
    def _to_pretest(row: asyncpg.Record) -> Pretest:
        return Pretest(
            id=row["id"],
            user_id=row["user_id"],
            course_id=row["course_id"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            status=row["status"],
        )

    @staticmethod
    def _to_answer(row: asyncpg.Record) -> PretestAnswer:
        return PretestAnswer(
            id=row["id"],
            pretest_id=row["pretest_id"],
            concept_id=row["concept_id"],
            question=row["question"],
            user_answer=row["user_answer"],
            correct_answer=row["correct_answer"],
            is_correct=row["is_correct"],
            created_at=row["created_at"],
        )
