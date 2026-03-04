from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class CoursePromotion:
    id: UUID
    course_id: UUID
    original_price: Decimal
    promo_price: Decimal
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    created_by: UUID
    created_at: datetime


@dataclass(frozen=True)
class ActivePromotion:
    promo_price: Decimal
    ends_at: datetime


class PromotionCreate(BaseModel):
    promo_price: Decimal
    starts_at: datetime
    ends_at: datetime


class PromotionResponse(BaseModel):
    id: UUID
    course_id: UUID
    original_price: Decimal
    promo_price: Decimal
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    created_by: UUID
    created_at: datetime


class PromotionListResponse(BaseModel):
    items: list[PromotionResponse]


class ActivePromotionResponse(BaseModel):
    promo_price: Decimal
    ends_at: datetime
