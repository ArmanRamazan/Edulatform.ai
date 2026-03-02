from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import asyncpg

from app.domain.payment import (
    EarningStatus,
    Payout,
    PayoutStatus,
    TeacherEarning,
)


class EarningsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_earning(
        self,
        teacher_id: UUID,
        course_id: UUID,
        payment_id: UUID,
        gross_amount: Decimal,
        commission_rate: Decimal,
    ) -> TeacherEarning:
        net_amount = gross_amount * (1 - commission_rate)
        row = await self._pool.fetchrow(
            """
            INSERT INTO teacher_earnings
                (teacher_id, course_id, payment_id, gross_amount, commission_rate, net_amount)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, teacher_id, course_id, payment_id,
                      gross_amount, commission_rate, net_amount, status, created_at
            """,
            teacher_id,
            course_id,
            payment_id,
            gross_amount,
            commission_rate,
            net_amount,
        )
        return self._to_earning_entity(row)

    async def get_earnings_by_teacher(
        self, teacher_id: UUID
    ) -> list[TeacherEarning]:
        rows = await self._pool.fetch(
            """
            SELECT id, teacher_id, course_id, payment_id,
                   gross_amount, commission_rate, net_amount, status, created_at
            FROM teacher_earnings
            WHERE teacher_id = $1
            ORDER BY created_at DESC
            """,
            teacher_id,
        )
        return [self._to_earning_entity(r) for r in rows]

    async def list_earnings(
        self, teacher_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[TeacherEarning], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, teacher_id, course_id, payment_id,
                       gross_amount, commission_rate, net_amount, status, created_at
                FROM teacher_earnings
                WHERE teacher_id = $1
                ORDER BY created_at DESC LIMIT $2 OFFSET $3
                """,
                teacher_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM teacher_earnings WHERE teacher_id = $1",
                teacher_id,
            )
        return [self._to_earning_entity(r) for r in rows], count

    async def create_payout(
        self, teacher_id: UUID, amount: Decimal
    ) -> Payout:
        row = await self._pool.fetchrow(
            """
            INSERT INTO payouts (teacher_id, amount)
            VALUES ($1, $2)
            RETURNING id, teacher_id, amount, stripe_transfer_id,
                      status, requested_at, completed_at
            """,
            teacher_id,
            amount,
        )
        return self._to_payout_entity(row)

    async def list_payouts(
        self, teacher_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Payout], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, teacher_id, amount, stripe_transfer_id,
                       status, requested_at, completed_at
                FROM payouts
                WHERE teacher_id = $1
                ORDER BY requested_at DESC LIMIT $2 OFFSET $3
                """,
                teacher_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM payouts WHERE teacher_id = $1",
                teacher_id,
            )
        return [self._to_payout_entity(r) for r in rows], count

    @staticmethod
    def _to_earning_entity(row: asyncpg.Record) -> TeacherEarning:
        return TeacherEarning(
            id=row["id"],
            teacher_id=row["teacher_id"],
            course_id=row["course_id"],
            payment_id=row["payment_id"],
            gross_amount=row["gross_amount"],
            commission_rate=row["commission_rate"],
            net_amount=row["net_amount"],
            status=EarningStatus(row["status"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_payout_entity(row: asyncpg.Record) -> Payout:
        return Payout(
            id=row["id"],
            teacher_id=row["teacher_id"],
            amount=row["amount"],
            stripe_transfer_id=row["stripe_transfer_id"],
            status=PayoutStatus(row["status"]),
            requested_at=row["requested_at"],
            completed_at=row["completed_at"],
        )
