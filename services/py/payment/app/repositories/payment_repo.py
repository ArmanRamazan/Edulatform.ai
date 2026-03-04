from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import asyncpg

from app.domain.payment import Payment, PaymentStatus


class PaymentRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        student_id: UUID,
        course_id: UUID,
        amount: Decimal,
    ) -> Payment:
        row = await self._pool.fetchrow(
            """
            INSERT INTO payments (student_id, course_id, amount)
            VALUES ($1, $2, $3)
            RETURNING id, student_id, course_id, amount, status, created_at
            """,
            student_id,
            course_id,
            amount,
        )
        return self._to_entity(row)

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, student_id, course_id, amount, status, created_at
            FROM payments WHERE id = $1
            """,
            payment_id,
        )
        return self._to_entity(row) if row else None

    async def list_by_student(
        self, student_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Payment], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, student_id, course_id, amount, status, created_at
                FROM payments WHERE student_id = $1
                ORDER BY created_at DESC LIMIT $2 OFFSET $3
                """,
                student_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM payments WHERE student_id = $1",
                student_id,
            )
        return [self._to_entity(r) for r in rows], count

    async def update_status(
        self, payment_id: UUID, status: PaymentStatus,
    ) -> Payment | None:
        row = await self._pool.fetchrow(
            """
            UPDATE payments SET status = $2
            WHERE id = $1
            RETURNING id, student_id, course_id, amount, status, created_at
            """,
            payment_id,
            str(status),
        )
        return self._to_entity(row) if row else None

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Payment:
        return Payment(
            id=row["id"],
            student_id=row["student_id"],
            course_id=row["course_id"],
            amount=row["amount"],
            status=PaymentStatus(row["status"]),
            created_at=row["created_at"],
        )
