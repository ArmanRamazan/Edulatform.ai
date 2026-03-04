from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass(frozen=True)
class Payment:
    id: UUID
    student_id: UUID
    course_id: UUID
    amount: Decimal
    status: PaymentStatus
    created_at: datetime


class PaymentCreate(BaseModel):
    course_id: UUID
    amount: Decimal = Field(gt=0)
    coupon_code: str | None = None


class PaymentResponse(BaseModel):
    id: UUID
    student_id: UUID
    course_id: UUID
    amount: Decimal
    status: PaymentStatus
    created_at: datetime


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int


class EarningStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"


class PayoutStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class TeacherEarning:
    id: UUID
    teacher_id: UUID
    course_id: UUID
    payment_id: UUID
    gross_amount: Decimal
    commission_rate: Decimal
    net_amount: Decimal
    status: EarningStatus
    created_at: datetime


@dataclass(frozen=True)
class Payout:
    id: UUID
    teacher_id: UUID
    amount: Decimal
    stripe_transfer_id: str | None
    status: PayoutStatus
    requested_at: datetime
    completed_at: datetime | None


class EarningResponse(BaseModel):
    id: UUID
    teacher_id: UUID
    course_id: UUID
    payment_id: UUID
    gross_amount: Decimal
    commission_rate: Decimal
    net_amount: Decimal
    status: EarningStatus
    created_at: datetime


class EarningsSummary(BaseModel):
    total_gross: Decimal
    total_net: Decimal
    total_pending: Decimal
    total_paid: Decimal
    earnings: list[EarningResponse]


class EarningListResponse(BaseModel):
    items: list[EarningResponse]
    total: int


class PayoutResponse(BaseModel):
    id: UUID
    teacher_id: UUID
    amount: Decimal
    stripe_transfer_id: str | None
    status: PayoutStatus
    requested_at: datetime
    completed_at: datetime | None


class PayoutListResponse(BaseModel):
    items: list[PayoutResponse]
    total: int


class PayoutCreate(BaseModel):
    amount: Decimal = Field(gt=0)
