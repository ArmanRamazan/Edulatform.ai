from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class DiscountType(StrEnum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


@dataclass(frozen=True)
class Coupon:
    id: UUID
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    max_uses: int | None
    current_uses: int
    valid_from: datetime
    valid_until: datetime
    course_id: UUID | None
    created_by: UUID
    is_active: bool
    created_at: datetime


@dataclass(frozen=True)
class CouponUsage:
    id: UUID
    coupon_id: UUID
    user_id: UUID
    payment_id: UUID | None
    used_at: datetime


@dataclass(frozen=True)
class DiscountResult:
    original_price: Decimal
    discount_amount: Decimal
    final_price: Decimal
    coupon_code: str


class CouponCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    discount_type: DiscountType
    discount_value: Decimal = Field(gt=0)
    max_uses: int | None = None
    valid_from: datetime
    valid_until: datetime
    course_id: UUID | None = None


class CouponValidate(BaseModel):
    code: str
    course_id: UUID
    amount: Decimal = Field(gt=0)


class DiscountResultResponse(BaseModel):
    original_price: Decimal
    discount_amount: Decimal
    final_price: Decimal
    coupon_code: str


class CouponResponse(BaseModel):
    id: UUID
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    max_uses: int | None
    current_uses: int
    valid_from: datetime
    valid_until: datetime
    course_id: UUID | None
    created_by: UUID
    is_active: bool
    created_at: datetime


class CouponListResponse(BaseModel):
    items: list[CouponResponse]
    total: int
