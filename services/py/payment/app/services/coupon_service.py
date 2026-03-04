from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from common.errors import AppError, ForbiddenError, NotFoundError
from app.domain.coupon import Coupon, DiscountResult, DiscountType
from app.repositories.coupon_repo import CouponRepository

_CODE_PATTERN = re.compile(r"^[A-Z0-9\-]+$")


class CouponService:
    def __init__(self, repo: CouponRepository) -> None:
        self._repo = repo

    async def create_coupon(
        self,
        admin_id: UUID,
        role: str,
        code: str,
        discount_type: DiscountType,
        discount_value: Decimal,
        max_uses: int | None,
        valid_from: datetime,
        valid_until: datetime,
        course_id: UUID | None,
    ) -> Coupon:
        if role != "admin":
            raise ForbiddenError("Only admins can create coupons")

        if not _CODE_PATTERN.match(code):
            raise AppError(
                "Code must be uppercase alphanumeric with hyphens only",
                status_code=400,
            )

        if discount_type == DiscountType.PERCENTAGE and discount_value > 100:
            raise AppError("Percentage discount cannot exceed 100", status_code=400)

        if valid_until <= valid_from:
            raise AppError("valid_until must be after valid_from", status_code=400)

        return await self._repo.create_coupon(
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            max_uses=max_uses,
            valid_from=valid_from,
            valid_until=valid_until,
            course_id=course_id,
            created_by=admin_id,
        )

    async def validate_coupon(
        self,
        code: str,
        course_id: UUID,
        user_id: UUID,
        original_price: Decimal,
    ) -> DiscountResult:
        coupon = await self._repo.get_coupon_by_code(code)
        if not coupon:
            raise NotFoundError("Coupon not found")

        self._check_coupon_valid(coupon, course_id)

        if await self._repo.has_user_used(coupon.id, user_id):
            raise AppError("Coupon already used by this user", status_code=400)

        discount_amount = self._calculate_discount(coupon, original_price)
        final_price = max(original_price - discount_amount, Decimal("0"))

        return DiscountResult(
            original_price=original_price,
            discount_amount=discount_amount,
            final_price=final_price,
            coupon_code=coupon.code,
        )

    async def apply_coupon(
        self,
        code: str,
        user_id: UUID,
        payment_id: UUID,
    ) -> None:
        coupon = await self._repo.get_coupon_by_code(code)
        if not coupon:
            raise NotFoundError("Coupon not found")
        await self._repo.increment_usage(coupon.id)
        await self._repo.record_usage(coupon.id, user_id, payment_id)

    async def deactivate_coupon(
        self,
        admin_id: UUID,
        role: str,
        coupon_id: UUID,
    ) -> None:
        if role != "admin":
            raise ForbiddenError("Only admins can deactivate coupons")
        success = await self._repo.deactivate_coupon(coupon_id)
        if not success:
            raise NotFoundError("Coupon not found")

    async def list_coupons(
        self,
        role: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Coupon], int]:
        if role != "admin":
            raise ForbiddenError("Only admins can list coupons")
        return await self._repo.list_coupons(limit, offset)

    @staticmethod
    def _check_coupon_valid(coupon: Coupon, course_id: UUID) -> None:
        now = datetime.now(timezone.utc)

        if not coupon.is_active:
            raise NotFoundError("Coupon is not active")

        if now < coupon.valid_from or now > coupon.valid_until:
            raise NotFoundError("Coupon is expired or not yet valid")

        if coupon.max_uses is not None and coupon.current_uses >= coupon.max_uses:
            raise NotFoundError("Coupon usage limit reached")

        if coupon.course_id is not None and coupon.course_id != course_id:
            raise NotFoundError("Coupon is not valid for this course")

    @staticmethod
    def _calculate_discount(coupon: Coupon, original_price: Decimal) -> Decimal:
        if coupon.discount_type == DiscountType.PERCENTAGE:
            return (original_price * coupon.discount_value / Decimal("100")).quantize(
                Decimal("0.01")
            )
        # Fixed discount, capped at original price
        return min(coupon.discount_value, original_price)
