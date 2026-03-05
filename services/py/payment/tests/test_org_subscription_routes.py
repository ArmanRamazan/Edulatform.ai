from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, AppError, NotFoundError, ConflictError
from common.security import create_access_token
from app.domain.org_subscription import (
    OrgSubscription,
    OrgSubscriptionStatus,
    PlanTier,
)
from app.routes.org_subscriptions import router
from app.services.org_subscription_service import OrgSubscriptionService


@pytest.fixture
def mock_org_sub_service():
    return AsyncMock(spec=OrgSubscriptionService)


@pytest.fixture
def test_app(mock_org_sub_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
        "stripe_webhook_secret": "whsec_test",
    })()
    main_module._org_subscription_service = mock_org_sub_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def admin_token(org_id):
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={
            "role": "tech_lead",
            "is_verified": True,
            "organization_id": str(org_id),
        },
    )


@pytest.fixture
def student_token():
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def sample_sub(org_id):
    return OrgSubscription(
        id=uuid4(),
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test123",
        stripe_customer_id="cus_test123",
        max_seats=20,
        current_seats=3,
        price_cents=100000,
        status=OrgSubscriptionStatus.ACTIVE,
        trial_ends_at=None,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
    )


# --- POST /org-subscriptions ---


@pytest.mark.asyncio
async def test_create_org_subscription(
    client, mock_org_sub_service, sample_sub, admin_token, org_id,
):
    mock_org_sub_service.create_subscription.return_value = sample_sub

    resp = await client.post("/org-subscriptions", json={
        "plan_tier": "pilot",
        "payment_method_id": "pm_test",
        "org_email": "org@example.com",
        "org_name": "Test Org",
    }, headers={"Authorization": f"Bearer {admin_token}"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["plan_tier"] == "pilot"
    assert body["status"] == "active"
    assert body["max_seats"] == 20


@pytest.mark.asyncio
async def test_create_org_subscription_already_exists(
    client, mock_org_sub_service, admin_token,
):
    mock_org_sub_service.create_subscription.side_effect = ConflictError(
        "Organization already has an active subscription",
    )

    resp = await client.post("/org-subscriptions", json={
        "plan_tier": "pilot",
        "payment_method_id": "pm_test",
        "org_email": "org@example.com",
        "org_name": "Test Org",
    }, headers={"Authorization": f"Bearer {admin_token}"})

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_org_subscription_no_org(client, student_token):
    resp = await client.post("/org-subscriptions", json={
        "plan_tier": "pilot",
        "payment_method_id": "pm_test",
        "org_email": "org@example.com",
        "org_name": "Test Org",
    }, headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 403


# --- GET /org-subscriptions/{org_id} ---


@pytest.mark.asyncio
async def test_get_org_subscription(
    client, mock_org_sub_service, sample_sub, admin_token, org_id,
):
    mock_org_sub_service.get_subscription.return_value = sample_sub

    resp = await client.get(
        f"/org-subscriptions/{org_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["organization_id"] == str(org_id)
    assert body["current_seats"] == 3


@pytest.mark.asyncio
async def test_get_org_subscription_not_found(
    client, mock_org_sub_service, admin_token, org_id,
):
    mock_org_sub_service.get_subscription.side_effect = NotFoundError(
        "No subscription found",
    )

    resp = await client.get(
        f"/org-subscriptions/{org_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_org_subscription_wrong_org(client, mock_org_sub_service):
    other_org_id = uuid4()
    token = create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={
            "role": "tech_lead",
            "is_verified": True,
            "organization_id": str(uuid4()),  # different org
        },
    )

    resp = await client.get(
        f"/org-subscriptions/{other_org_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403


# --- POST /org-subscriptions/{org_id}/cancel ---


@pytest.mark.asyncio
async def test_cancel_org_subscription(
    client, mock_org_sub_service, sample_sub, admin_token, org_id,
):
    canceled = OrgSubscription(
        id=sample_sub.id,
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test123",
        stripe_customer_id="cus_test123",
        max_seats=20,
        current_seats=3,
        price_cents=100000,
        status=OrgSubscriptionStatus.CANCELED,
        trial_ends_at=None,
        current_period_start=sample_sub.current_period_start,
        current_period_end=sample_sub.current_period_end,
        created_at=sample_sub.created_at,
    )
    mock_org_sub_service.cancel_subscription.return_value = canceled

    resp = await client.post(
        f"/org-subscriptions/{org_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_cancel_org_subscription_wrong_org(client):
    other_org_id = uuid4()
    token = create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={
            "role": "tech_lead",
            "is_verified": True,
            "organization_id": str(uuid4()),
        },
    )

    resp = await client.post(
        f"/org-subscriptions/{other_org_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403


# --- POST /webhooks/stripe-org ---


@pytest.mark.asyncio
async def test_stripe_org_webhook(client, mock_org_sub_service):
    mock_org_sub_service.handle_webhook.return_value = None

    # We mock the stripe client at service level, so just post raw
    import app.main as main_module
    original_stripe = getattr(main_module, "_stripe_client", None)
    mock_stripe = AsyncMock()
    mock_stripe.construct_webhook_event.return_value = {
        "type": "invoice.paid",
        "data": {
            "object": {
                "subscription": "sub_test123",
            },
        },
    }
    main_module._stripe_client = mock_stripe

    resp = await client.post(
        "/webhooks/stripe-org",
        content=b'{"test": true}',
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": "t=123,v1=abc",
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    mock_org_sub_service.handle_webhook.assert_called_once_with(
        event_type="invoice.paid",
        stripe_subscription_id="sub_test123",
    )

    # Restore
    if original_stripe is not None:
        main_module._stripe_client = original_stripe
