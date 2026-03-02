from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.subscription import SubscriptionPlan, SubscriptionStatus, UserSubscription
from app.repositories.subscription_repo import SubscriptionRepository


@pytest.fixture
def mock_pool() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repo(mock_pool: AsyncMock) -> SubscriptionRepository:
    return SubscriptionRepository(mock_pool)


@pytest.fixture
def plan_row() -> dict:
    return {
        "id": uuid4(),
        "name": "pro",
        "stripe_price_id": "price_123",
        "price_monthly": Decimal("19.99"),
        "price_yearly": Decimal("199.99"),
        "ai_credits_daily": -1,
        "features": '{"courses": true}',
        "created_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def subscription_row() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": uuid4(),
        "user_id": uuid4(),
        "plan_id": uuid4(),
        "plan_name": "pro",
        "stripe_subscription_id": "sub_123",
        "stripe_customer_id": "cus_123",
        "status": "active",
        "current_period_start": now,
        "current_period_end": now,
        "cancel_at_period_end": False,
        "created_at": now,
        "updated_at": now,
    }


class TestGetPlanByName:
    async def test_returns_none_when_not_found(
        self, repo: SubscriptionRepository, mock_pool: AsyncMock
    ) -> None:
        mock_pool.fetchrow.return_value = None
        result = await repo.get_plan_by_name("nonexistent")
        assert result is None

    async def test_returns_plan_entity(
        self, repo: SubscriptionRepository, mock_pool: AsyncMock, plan_row: dict
    ) -> None:
        mock_pool.fetchrow.return_value = plan_row
        result = await repo.get_plan_by_name("pro")
        assert isinstance(result, SubscriptionPlan)
        assert result.name == "pro"
        assert result.ai_credits_daily == -1


class TestGetPlanById:
    async def test_returns_none_when_not_found(
        self, repo: SubscriptionRepository, mock_pool: AsyncMock
    ) -> None:
        mock_pool.fetchrow.return_value = None
        result = await repo.get_plan_by_id(uuid4())
        assert result is None

    async def test_returns_plan_entity(
        self, repo: SubscriptionRepository, mock_pool: AsyncMock, plan_row: dict
    ) -> None:
        mock_pool.fetchrow.return_value = plan_row
        result = await repo.get_plan_by_id(plan_row["id"])
        assert isinstance(result, SubscriptionPlan)


class TestListPlans:
    async def test_maps_all_rows(
        self, repo: SubscriptionRepository, mock_pool: AsyncMock, plan_row: dict
    ) -> None:
        mock_pool.fetch.return_value = [plan_row, plan_row]
        result = await repo.list_plans()
        assert len(result) == 2
        assert all(isinstance(p, SubscriptionPlan) for p in result)

    async def test_empty_list(
        self, repo: SubscriptionRepository, mock_pool: AsyncMock
    ) -> None:
        mock_pool.fetch.return_value = []
        result = await repo.list_plans()
        assert result == []


class TestGetUserSubscription:
    async def test_returns_none_when_not_found(
        self, repo: SubscriptionRepository, mock_pool: AsyncMock
    ) -> None:
        mock_pool.fetchrow.return_value = None
        result = await repo.get_user_subscription(uuid4())
        assert result is None

    async def test_returns_entity(
        self, repo: SubscriptionRepository, mock_pool: AsyncMock, subscription_row: dict
    ) -> None:
        mock_pool.fetchrow.return_value = subscription_row
        result = await repo.get_user_subscription(subscription_row["user_id"])
        assert isinstance(result, UserSubscription)
        assert result.status == SubscriptionStatus.ACTIVE


class TestCreateUserSubscription:
    async def test_returns_entity(
        self, repo: SubscriptionRepository, mock_pool: AsyncMock, subscription_row: dict
    ) -> None:
        mock_pool.fetchrow.return_value = subscription_row
        now = datetime.now(timezone.utc)
        result = await repo.create_user_subscription(
            user_id=subscription_row["user_id"],
            plan_id=subscription_row["plan_id"],
            stripe_subscription_id="sub_123",
            stripe_customer_id="cus_123",
            status=SubscriptionStatus.ACTIVE,
            period_start=now,
            period_end=now,
        )
        assert isinstance(result, UserSubscription)
        assert result.stripe_subscription_id == "sub_123"


class TestUpdateUserSubscription:
    async def test_returns_updated_entity(
        self, repo: SubscriptionRepository, mock_pool: AsyncMock, subscription_row: dict
    ) -> None:
        subscription_row["status"] = "canceled"
        mock_pool.fetchrow.return_value = subscription_row
        result = await repo.update_user_subscription(
            user_id=subscription_row["user_id"],
            status=SubscriptionStatus.CANCELED,
        )
        assert isinstance(result, UserSubscription)
        assert result.status == SubscriptionStatus.CANCELED
