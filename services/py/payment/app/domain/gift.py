from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class GiftStatus(StrEnum):
    PURCHASED = "purchased"
    REDEEMED = "redeemed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class GiftPurchase:
    id: UUID
    buyer_id: UUID
    recipient_email: str
    course_id: UUID
    payment_id: UUID
    gift_code: str
    status: GiftStatus
    message: str | None
    created_at: datetime
    redeemed_at: datetime | None
    redeemed_by: UUID | None
    expires_at: datetime


class GiftCreate(BaseModel):
    course_id: UUID
    recipient_email: str = Field(min_length=1, max_length=255)
    message: str | None = Field(default=None, max_length=500)


class GiftRedeem(BaseModel):
    gift_code: str = Field(min_length=14, max_length=14)


class GiftResponse(BaseModel):
    id: UUID
    buyer_id: UUID
    recipient_email: str
    course_id: UUID
    payment_id: UUID
    gift_code: str
    status: GiftStatus
    message: str | None
    created_at: datetime
    redeemed_at: datetime | None
    redeemed_by: UUID | None
    expires_at: datetime


class GiftInfoResponse(BaseModel):
    gift_code: str
    course_id: UUID
    status: GiftStatus
    message: str | None
    expires_at: datetime


class GiftListResponse(BaseModel):
    items: list[GiftResponse]
    total: int
