from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from uuid import UUID

import asyncpg

from app.domain.promotion import CoursePromotion

_COLUMNS = "id, course_id, original_price, promo_price, starts_at, ends_at, is_active, created_by, created_at"


class PromotionRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_promotion(
        self,
        course_id: UUID,
        original_price: Decimal,
        promo_price: Decimal,
        starts_at: datetime,
        ends_at: datetime,
        created_by: UUID,
    ) -> CoursePromotion:
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO course_promotions (course_id, original_price, promo_price, starts_at, ends_at, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING {_COLUMNS}
            """,
            course_id, original_price, promo_price, starts_at, ends_at, created_by,
        )
        return self._to_entity(row)

    async def get_promotion(self, promotion_id: UUID) -> CoursePromotion | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM course_promotions WHERE id = $1",
            promotion_id,
        )
        return self._to_entity(row) if row else None

    async def get_active_promotion(self, course_id: UUID) -> CoursePromotion | None:
        row = await self._pool.fetchrow(
            f"""SELECT {_COLUMNS} FROM course_promotions
                WHERE course_id = $1 AND is_active = true
                  AND starts_at <= now() AND ends_at > now()
                ORDER BY created_at DESC LIMIT 1""",
            course_id,
        )
        return self._to_entity(row) if row else None

    async def get_active_promotions_batch(
        self, course_ids: list[UUID],
    ) -> dict[UUID, CoursePromotion]:
        if not course_ids:
            return {}
        rows = await self._pool.fetch(
            f"""SELECT DISTINCT ON (course_id) {_COLUMNS}
                FROM course_promotions
                WHERE course_id = ANY($1) AND is_active = true
                  AND starts_at <= now() AND ends_at > now()
                ORDER BY course_id, created_at DESC""",
            course_ids,
        )
        return {row["course_id"]: self._to_entity(row) for row in rows}

    async def get_course_promotions(self, course_id: UUID) -> list[CoursePromotion]:
        rows = await self._pool.fetch(
            f"""SELECT {_COLUMNS} FROM course_promotions
                WHERE course_id = $1
                ORDER BY created_at DESC""",
            course_id,
        )
        return [self._to_entity(r) for r in rows]

    async def delete_promotion(self, promotion_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM course_promotions WHERE id = $1", promotion_id,
        )
        return result == "DELETE 1"

    async def deactivate_expired(self) -> int:
        result = await self._pool.execute(
            "UPDATE course_promotions SET is_active = false WHERE is_active = true AND ends_at < now()",
        )
        return int(result.split()[-1])

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> CoursePromotion:
        return CoursePromotion(
            id=row["id"],
            course_id=row["course_id"],
            original_price=row["original_price"],
            promo_price=row["promo_price"],
            starts_at=row["starts_at"],
            ends_at=row["ends_at"],
            is_active=row["is_active"],
            created_by=row["created_by"],
            created_at=row["created_at"],
        )
