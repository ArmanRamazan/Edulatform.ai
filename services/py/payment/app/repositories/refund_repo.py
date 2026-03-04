from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.domain.refund import Refund, RefundStatus


class RefundRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_refund(
        self,
        payment_id: UUID,
        user_id: UUID,
        reason: str,
        amount: Decimal,
    ) -> Refund:
        row = await self._pool.fetchrow(
            """
            INSERT INTO refunds (payment_id, user_id, reason, amount)
            VALUES ($1, $2, $3, $4)
            RETURNING id, payment_id, user_id, reason, status, amount,
                      admin_note, requested_at, processed_at
            """,
            payment_id,
            user_id,
            reason,
            amount,
        )
        return self._to_entity(row)

    async def get_refund(self, refund_id: UUID) -> Refund | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, payment_id, user_id, reason, status, amount,
                   admin_note, requested_at, processed_at
            FROM refunds WHERE id = $1
            """,
            refund_id,
        )
        return self._to_entity(row) if row else None

    async def get_by_payment_id(self, payment_id: UUID) -> Refund | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, payment_id, user_id, reason, status, amount,
                   admin_note, requested_at, processed_at
            FROM refunds WHERE payment_id = $1
            """,
            payment_id,
        )
        return self._to_entity(row) if row else None

    async def get_user_refunds(
        self, user_id: UUID, limit: int = 20, offset: int = 0,
    ) -> tuple[list[Refund], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, payment_id, user_id, reason, status, amount,
                       admin_note, requested_at, processed_at
                FROM refunds WHERE user_id = $1
                ORDER BY requested_at DESC LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM refunds WHERE user_id = $1",
                user_id,
            )
        return [self._to_entity(r) for r in rows], count

    async def list_all_refunds(
        self,
        status_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Refund], int]:
        async with self._pool.acquire() as conn:
            if status_filter:
                rows = await conn.fetch(
                    """
                    SELECT id, payment_id, user_id, reason, status, amount,
                           admin_note, requested_at, processed_at
                    FROM refunds WHERE status = $1
                    ORDER BY requested_at DESC LIMIT $2 OFFSET $3
                    """,
                    status_filter,
                    limit,
                    offset,
                )
                count = await conn.fetchval(
                    "SELECT count(*) FROM refunds WHERE status = $1",
                    status_filter,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, payment_id, user_id, reason, status, amount,
                           admin_note, requested_at, processed_at
                    FROM refunds
                    ORDER BY requested_at DESC LIMIT $1 OFFSET $2
                    """,
                    limit,
                    offset,
                )
                count = await conn.fetchval("SELECT count(*) FROM refunds")
        return [self._to_entity(r) for r in rows], count

    async def update_status(
        self,
        refund_id: UUID,
        status: RefundStatus,
        admin_note: str | None = None,
        processed_at: datetime | None = None,
    ) -> Refund:
        row = await self._pool.fetchrow(
            """
            UPDATE refunds
            SET status = $2, admin_note = $3, processed_at = $4
            WHERE id = $1
            RETURNING id, payment_id, user_id, reason, status, amount,
                      admin_note, requested_at, processed_at
            """,
            refund_id,
            str(status),
            admin_note,
            processed_at,
        )
        return self._to_entity(row)

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Refund:
        return Refund(
            id=row["id"],
            payment_id=row["payment_id"],
            user_id=row["user_id"],
            reason=row["reason"],
            status=RefundStatus(row["status"]),
            amount=row["amount"],
            admin_note=row["admin_note"],
            requested_at=row["requested_at"],
            processed_at=row["processed_at"],
        )
