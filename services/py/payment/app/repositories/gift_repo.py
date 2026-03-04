from __future__ import annotations

from datetime import datetime
from uuid import UUID

import asyncpg

from app.domain.gift import GiftPurchase, GiftStatus


class GiftRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_gift(
        self,
        buyer_id: UUID,
        recipient_email: str,
        course_id: UUID,
        payment_id: UUID,
        gift_code: str,
        message: str | None,
        expires_at: datetime,
    ) -> GiftPurchase:
        row = await self._pool.fetchrow(
            """
            INSERT INTO gift_purchases
                (buyer_id, recipient_email, course_id, payment_id, gift_code, message, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, buyer_id, recipient_email, course_id, payment_id, gift_code,
                      status, message, created_at, redeemed_at, redeemed_by, expires_at
            """,
            buyer_id,
            recipient_email,
            course_id,
            payment_id,
            gift_code,
            message,
            expires_at,
        )
        return self._to_entity(row)

    async def get_gift_by_code(self, gift_code: str) -> GiftPurchase | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, buyer_id, recipient_email, course_id, payment_id, gift_code,
                   status, message, created_at, redeemed_at, redeemed_by, expires_at
            FROM gift_purchases WHERE gift_code = $1
            """,
            gift_code,
        )
        return self._to_entity(row) if row else None

    async def get_sent_gifts(
        self, buyer_id: UUID, limit: int = 20, offset: int = 0,
    ) -> tuple[list[GiftPurchase], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, buyer_id, recipient_email, course_id, payment_id, gift_code,
                       status, message, created_at, redeemed_at, redeemed_by, expires_at
                FROM gift_purchases WHERE buyer_id = $1
                ORDER BY created_at DESC LIMIT $2 OFFSET $3
                """,
                buyer_id,
                limit,
                offset,
            )
            count = await conn.fetchval(
                "SELECT count(*) FROM gift_purchases WHERE buyer_id = $1",
                buyer_id,
            )
        return [self._to_entity(r) for r in rows], count

    async def redeem_gift(self, gift_code: str, user_id: UUID) -> GiftPurchase:
        row = await self._pool.fetchrow(
            """
            UPDATE gift_purchases
            SET status = 'redeemed', redeemed_at = now(), redeemed_by = $2
            WHERE gift_code = $1
            RETURNING id, buyer_id, recipient_email, course_id, payment_id, gift_code,
                      status, message, created_at, redeemed_at, redeemed_by, expires_at
            """,
            gift_code,
            user_id,
        )
        return self._to_entity(row)

    async def expire_gifts(self) -> int:
        result = await self._pool.execute(
            """
            UPDATE gift_purchases
            SET status = 'expired'
            WHERE expires_at < now() AND status = 'purchased'
            """,
        )
        # asyncpg returns "UPDATE N"
        return int(result.split()[-1])

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> GiftPurchase:
        return GiftPurchase(
            id=row["id"],
            buyer_id=row["buyer_id"],
            recipient_email=row["recipient_email"],
            course_id=row["course_id"],
            payment_id=row["payment_id"],
            gift_code=row["gift_code"],
            status=GiftStatus(row["status"]),
            message=row["message"],
            created_at=row["created_at"],
            redeemed_at=row["redeemed_at"],
            redeemed_by=row["redeemed_by"],
            expires_at=row["expires_at"],
        )
