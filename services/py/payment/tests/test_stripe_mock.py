import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from uuid import uuid4

from app.services.stripe_mock import MockStripeService, create_stripe_client
from app.config import Settings


@pytest.fixture
def mock_service():
    return MockStripeService()


# --- get_org_subscription ---


async def test_mock_returns_active_org_subscription(mock_service):
    org_id = uuid4()

    result = await mock_service.get_org_subscription(org_id)

    assert result["id"] == "sub_mock_demo"
    assert result["org_id"] == org_id
    assert result["plan"] == "enterprise"
    assert result["status"] == "active"
    assert result["current_seats"] == 10
    assert result["max_seats"] == 50
    assert result["price_cents"] == 100000
    assert result["currency"] == "usd"
    assert result["current_period_start"] == "2026-01-01"
    assert result["current_period_end"] == "2026-12-31"


# --- get_user_subscription ---


async def test_mock_returns_active_user_subscription(mock_service):
    user_id = uuid4()

    result = await mock_service.get_user_subscription(user_id)

    assert result["status"] == "active"
    assert result["user_id"] == user_id
    assert "id" in result
    assert "current_period_start" in result
    assert "current_period_end" in result


# --- create_payment ---


async def test_mock_returns_payment_success(mock_service):
    data = {"amount": 9900, "currency": "usd", "user_id": str(uuid4())}

    result = await mock_service.create_payment(data)

    assert result["id"].startswith("pay_mock_")
    assert result["status"] == "succeeded"


async def test_mock_payment_echoes_amount_and_currency(mock_service):
    data = {"amount": 4999, "currency": "eur"}

    result = await mock_service.create_payment(data)

    assert result["amount"] == 4999
    assert result["currency"] == "eur"


# --- create_stripe_client factory ---


def test_mock_activated_when_no_key():
    settings = Settings(stripe_secret_key="")

    client = create_stripe_client(settings)

    assert isinstance(client, MockStripeService)


def test_real_client_when_key_set():
    from app.repositories.stripe_client import StripeClient

    settings = Settings(stripe_secret_key="sk_test_fakekeyfortesting")

    client = create_stripe_client(settings)

    assert isinstance(client, StripeClient)


# --- StripeClient-compatible duck-type methods ---


async def test_mock_create_customer_returns_id(mock_service):
    result = await mock_service.create_customer(
        email="test@example.com", name="Test Org"
    )

    assert isinstance(result, str)
    assert result.startswith("cus_mock_")


async def test_mock_create_subscription_returns_dict(mock_service):
    result = await mock_service.create_subscription(
        customer_id="cus_mock_demo",
        price_id="price_enterprise_monthly",
        payment_method_id="pm_mock",
    )

    assert result["id"].startswith("sub_mock_")
    assert result["status"] == "active"
    assert "current_period_start" in result
    assert "current_period_end" in result


async def test_mock_cancel_subscription_returns_canceled(mock_service):
    result = await mock_service.cancel_subscription("sub_mock_demo")

    assert result["id"] == "sub_mock_demo"
    assert result["status"] == "canceled"
