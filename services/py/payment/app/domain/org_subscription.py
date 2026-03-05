from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class PlanTier(StrEnum):
    PILOT = "pilot"
    ENTERPRISE = "enterprise"


class OrgSubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"


PLAN_TIERS: dict[PlanTier, dict] = {
    PlanTier.PILOT: {
        "max_seats": 20,
        "price_cents": 100000,
        "stripe_price_id": "price_pilot_monthly",
    },
    PlanTier.ENTERPRISE: {
        "max_seats": 999,
        "price_cents": 1000000,
        "stripe_price_id": "price_enterprise_monthly",
    },
}


@dataclass(frozen=True)
class OrgSubscription:
    id: UUID
    organization_id: UUID
    plan_tier: PlanTier
    stripe_subscription_id: str | None
    stripe_customer_id: str | None
    max_seats: int
    current_seats: int
    price_cents: int
    status: OrgSubscriptionStatus
    trial_ends_at: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    created_at: datetime


class OrgSubscriptionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    plan_tier: str
    max_seats: int
    current_seats: int
    price_cents: int
    status: str
    trial_ends_at: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    created_at: datetime


class OrgSubscriptionCreateRequest(BaseModel):
    plan_tier: str
    payment_method_id: str
    org_email: str
    org_name: str
