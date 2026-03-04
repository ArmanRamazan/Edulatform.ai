from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class RefundStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"


@dataclass(frozen=True)
class Refund:
    id: UUID
    payment_id: UUID
    user_id: UUID
    reason: str
    status: RefundStatus
    amount: Decimal
    admin_note: str | None
    requested_at: datetime
    processed_at: datetime | None


class RefundCreate(BaseModel):
    payment_id: UUID
    reason: str = Field(min_length=1, max_length=1000)


class RefundReject(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class RefundResponse(BaseModel):
    id: UUID
    payment_id: UUID
    user_id: UUID
    reason: str
    status: RefundStatus
    amount: Decimal
    admin_note: str | None
    requested_at: datetime
    processed_at: datetime | None


class RefundListResponse(BaseModel):
    items: list[RefundResponse]
    total: int
