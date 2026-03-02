from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.subscription import (
    SubscriptionPlan,
    SubscriptionPlanResponse,
    SubscriptionResponse,
    SubscriptionStatus,
    UserSubscription,
)


@pytest.fixture
def plan() -> SubscriptionPlan:
    return SubscriptionPlan(
        id=uuid4(),
        name="pro",
        stripe_price_id="price_123",
        price_monthly=Decimal("19.99"),
        price_yearly=Decimal("199.99"),
        ai_credits_daily=-1,
        features={"courses": True, "ai_features": "unlimited"},
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def subscription() -> UserSubscription:
    now = datetime.now(timezone.utc)
    return UserSubscription(
        id=uuid4(),
        user_id=uuid4(),
        plan_id=uuid4(),
        plan_name="pro",
        stripe_subscription_id="sub_123",
        stripe_customer_id="cus_123",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now,
        cancel_at_period_end=False,
        created_at=now,
        updated_at=now,
    )


class TestSubscriptionPlanEntity:
    def test_frozen_cannot_mutate(self, plan: SubscriptionPlan) -> None:
        with pytest.raises(FrozenInstanceError):
            plan.name = "hacked"  # type: ignore[misc]

    def test_fields(self, plan: SubscriptionPlan) -> None:
        assert plan.name == "pro"
        assert plan.price_monthly == Decimal("19.99")
        assert plan.ai_credits_daily == -1

    def test_unlimited_credits_convention(self) -> None:
        plan = SubscriptionPlan(
            id=uuid4(),
            name="pro",
            stripe_price_id=None,
            price_monthly=Decimal("19.99"),
            price_yearly=None,
            ai_credits_daily=-1,
            features={},
            created_at=datetime.now(timezone.utc),
        )
        assert plan.ai_credits_daily == -1


class TestUserSubscriptionEntity:
    def test_frozen_cannot_mutate(self, subscription: UserSubscription) -> None:
        with pytest.raises(FrozenInstanceError):
            subscription.status = SubscriptionStatus.CANCELED  # type: ignore[misc]

    def test_status_enum_values(self) -> None:
        assert SubscriptionStatus.ACTIVE == "active"
        assert SubscriptionStatus.CANCELED == "canceled"
        assert SubscriptionStatus.PAST_DUE == "past_due"


class TestPydanticModels:
    def test_subscription_plan_response(self, plan: SubscriptionPlan) -> None:
        resp = SubscriptionPlanResponse(
            id=plan.id,
            name=plan.name,
            price_monthly=plan.price_monthly,
            price_yearly=plan.price_yearly,
            ai_credits_daily=plan.ai_credits_daily,
            features=plan.features,
        )
        data = resp.model_dump()
        assert data["name"] == "pro"
        assert data["price_monthly"] == Decimal("19.99")

    def test_subscription_response(self, subscription: UserSubscription) -> None:
        resp = SubscriptionResponse(
            id=subscription.id,
            user_id=subscription.user_id,
            plan_id=subscription.plan_id,
            plan_name=subscription.plan_name,
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            created_at=subscription.created_at,
        )
        data = resp.model_dump()
        assert data["plan_name"] == "pro"
        assert data["status"] == SubscriptionStatus.ACTIVE
