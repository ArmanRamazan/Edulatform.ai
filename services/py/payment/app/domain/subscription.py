from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"


@dataclass(frozen=True)
class SubscriptionPlan:
    id: UUID
    name: str
    stripe_price_id: str | None
    price_monthly: Decimal
    price_yearly: Decimal | None
    ai_credits_daily: int
    features: dict
    created_at: datetime


@dataclass(frozen=True)
class UserSubscription:
    id: UUID
    user_id: UUID
    plan_id: UUID
    plan_name: str
    stripe_subscription_id: str | None
    stripe_customer_id: str | None
    status: SubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: datetime


class SubscriptionPlanResponse(BaseModel):
    id: UUID
    name: str
    price_monthly: Decimal
    price_yearly: Decimal | None
    ai_credits_daily: int
    features: dict


class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    plan_id: UUID
    plan_name: str
    status: SubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    created_at: datetime


class SubscriptionCreateRequest(BaseModel):
    plan_id: UUID
    payment_method_id: str
