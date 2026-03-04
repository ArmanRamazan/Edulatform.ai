from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from uuid import UUID

import asyncpg

from app.domain.coupon import Coupon, CouponUsage, DiscountType


class CouponRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_coupon(
        self,
        code: str,
        discount_type: DiscountType,
        discount_value: Decimal,
        max_uses: int | None,
        valid_from: datetime,
        valid_until: datetime,
        course_id: UUID | None,
        created_by: UUID,
    ) -> Coupon:
        row = await self._pool.fetchrow(
            """
            INSERT INTO coupons (code, discount_type, discount_value, max_uses,
                                 valid_from, valid_until, course_id, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, code, discount_type, discount_value, max_uses,
                      current_uses, valid_from, valid_until, course_id,
                      created_by, is_active, created_at
            """,
            code, str(discount_type), discount_value, max_uses,
            valid_from, valid_until, course_id, created_by,
        )
        return self._to_entity(row)

    async def get_coupon_by_code(self, code: str) -> Coupon | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, code, discount_type, discount_value, max_uses,
                   current_uses, valid_from, valid_until, course_id,
                   created_by, is_active, created_at
            FROM coupons WHERE code = $1
            """,
            code,
        )
        return self._to_entity(row) if row else None

    async def get_coupon(self, coupon_id: UUID) -> Coupon | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, code, discount_type, discount_value, max_uses,
                   current_uses, valid_from, valid_until, course_id,
                   created_by, is_active, created_at
            FROM coupons WHERE id = $1
            """,
            coupon_id,
        )
        return self._to_entity(row) if row else None

    async def list_coupons(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[Coupon], int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, code, discount_type, discount_value, max_uses,
                       current_uses, valid_from, valid_until, course_id,
                       created_by, is_active, created_at
                FROM coupons ORDER BY created_at DESC LIMIT $1 OFFSET $2
                """,
                limit, offset,
            )
            count = await conn.fetchval("SELECT count(*) FROM coupons")
        return [self._to_entity(r) for r in rows], count

    async def deactivate_coupon(self, coupon_id: UUID) -> bool:
        result = await self._pool.execute(
            "UPDATE coupons SET is_active = false WHERE id = $1 AND is_active = true",
            coupon_id,
        )
        return result == "UPDATE 1"

    async def increment_usage(self, coupon_id: UUID) -> None:
        await self._pool.execute(
            "UPDATE coupons SET current_uses = current_uses + 1 WHERE id = $1",
            coupon_id,
        )

    async def record_usage(
        self, coupon_id: UUID, user_id: UUID, payment_id: UUID | None
    ) -> CouponUsage:
        row = await self._pool.fetchrow(
            """
            INSERT INTO coupon_usages (coupon_id, user_id, payment_id)
            VALUES ($1, $2, $3)
            RETURNING id, coupon_id, user_id, payment_id, used_at
            """,
            coupon_id, user_id, payment_id,
        )
        return CouponUsage(
            id=row["id"],
            coupon_id=row["coupon_id"],
            user_id=row["user_id"],
            payment_id=row["payment_id"],
            used_at=row["used_at"],
        )

    async def has_user_used(self, coupon_id: UUID, user_id: UUID) -> bool:
        count = await self._pool.fetchval(
            "SELECT count(*) FROM coupon_usages WHERE coupon_id = $1 AND user_id = $2",
            coupon_id, user_id,
        )
        return count > 0

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Coupon:
        return Coupon(
            id=row["id"],
            code=row["code"],
            discount_type=DiscountType(row["discount_type"]),
            discount_value=row["discount_value"],
            max_uses=row["max_uses"],
            current_uses=row["current_uses"],
            valid_from=row["valid_from"],
            valid_until=row["valid_until"],
            course_id=row["course_id"],
            created_by=row["created_by"],
            is_active=row["is_active"],
            created_at=row["created_at"],
        )
