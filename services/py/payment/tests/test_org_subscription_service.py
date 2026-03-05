from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from common.errors import AppError, NotFoundError, ConflictError
from app.domain.org_subscription import (
    OrgSubscription,
    OrgSubscriptionStatus,
    PlanTier,
    PLAN_TIERS,
)
from app.repositories.org_subscription_repo import OrgSubscriptionRepository
from app.repositories.stripe_client import StripeClient
from app.services.org_subscription_service import OrgSubscriptionService


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=OrgSubscriptionRepository)


@pytest.fixture
def mock_stripe():
    return AsyncMock(spec=StripeClient)


@pytest.fixture
def service(mock_repo, mock_stripe):
    return OrgSubscriptionService(repo=mock_repo, stripe_client=mock_stripe)


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def sub_id():
    return uuid4()


@pytest.fixture
def sample_sub(sub_id, org_id):
    return OrgSubscription(
        id=sub_id,
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test123",
        stripe_customer_id="cus_test123",
        max_seats=20,
        current_seats=0,
        price_cents=100000,
        status=OrgSubscriptionStatus.ACTIVE,
        trial_ends_at=None,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
    )


# --- PLAN_TIERS config ---


def test_pilot_tier_config():
    tier = PLAN_TIERS[PlanTier.PILOT]
    assert tier["max_seats"] == 20
    assert tier["price_cents"] == 100000


def test_enterprise_tier_config():
    tier = PLAN_TIERS[PlanTier.ENTERPRISE]
    assert tier["max_seats"] == 999
    assert tier["price_cents"] == 1000000


# --- create_subscription ---


@pytest.mark.asyncio
async def test_create_subscription_pilot(service, mock_repo, mock_stripe, org_id, sample_sub):
    mock_repo.get_by_org.return_value = None
    mock_stripe.create_customer.return_value = "cus_test123"
    mock_stripe.create_subscription.return_value = {
        "id": "sub_test123",
        "status": "active",
        "current_period_start": 1700000000,
        "current_period_end": 1702592000,
    }
    mock_repo.create.return_value = sample_sub

    result = await service.create_subscription(
        organization_id=org_id,
        plan_tier="pilot",
        payment_method_id="pm_test",
        org_email="org@example.com",
        org_name="Test Org",
    )

    assert result.plan_tier == PlanTier.PILOT
    assert result.status == OrgSubscriptionStatus.ACTIVE
    mock_stripe.create_customer.assert_called_once_with(
        email="org@example.com", name="Test Org",
    )
    mock_stripe.create_subscription.assert_called_once()
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_subscription_already_exists(service, mock_repo, org_id, sample_sub):
    mock_repo.get_by_org.return_value = sample_sub

    with pytest.raises(ConflictError, match="already has.*subscription"):
        await service.create_subscription(
            organization_id=org_id,
            plan_tier="pilot",
            payment_method_id="pm_test",
            org_email="org@example.com",
            org_name="Test Org",
        )


@pytest.mark.asyncio
async def test_create_subscription_invalid_tier(service, mock_repo, org_id):
    mock_repo.get_by_org.return_value = None

    with pytest.raises(AppError, match="Invalid plan tier"):
        await service.create_subscription(
            organization_id=org_id,
            plan_tier="invalid_tier",
            payment_method_id="pm_test",
            org_email="org@example.com",
            org_name="Test Org",
        )


# --- check_seat_limit ---


@pytest.mark.asyncio
async def test_check_seat_limit_within(service, mock_repo, org_id, sample_sub):
    mock_repo.get_by_org.return_value = sample_sub

    result = await service.check_seat_limit(org_id)

    assert result is True


@pytest.mark.asyncio
async def test_check_seat_limit_exceeded(service, mock_repo, org_id, sub_id):
    full_sub = OrgSubscription(
        id=sub_id,
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test",
        stripe_customer_id="cus_test",
        max_seats=20,
        current_seats=20,
        price_cents=100000,
        status=OrgSubscriptionStatus.ACTIVE,
        trial_ends_at=None,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
    )
    mock_repo.get_by_org.return_value = full_sub

    result = await service.check_seat_limit(org_id)

    assert result is False


@pytest.mark.asyncio
async def test_check_seat_limit_no_subscription(service, mock_repo, org_id):
    mock_repo.get_by_org.return_value = None

    with pytest.raises(NotFoundError, match="No subscription"):
        await service.check_seat_limit(org_id)


@pytest.mark.asyncio
async def test_check_seat_limit_inactive(service, mock_repo, org_id, sub_id):
    canceled_sub = OrgSubscription(
        id=sub_id,
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test",
        stripe_customer_id="cus_test",
        max_seats=20,
        current_seats=5,
        price_cents=100000,
        status=OrgSubscriptionStatus.CANCELED,
        trial_ends_at=None,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
    )
    mock_repo.get_by_org.return_value = canceled_sub

    with pytest.raises(AppError, match="not active"):
        await service.check_seat_limit(org_id)


# --- add_seat ---


@pytest.mark.asyncio
async def test_add_seat_success(service, mock_repo, org_id, sample_sub):
    mock_repo.get_by_org.return_value = sample_sub
    updated = OrgSubscription(
        id=sample_sub.id,
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test123",
        stripe_customer_id="cus_test123",
        max_seats=20,
        current_seats=1,
        price_cents=100000,
        status=OrgSubscriptionStatus.ACTIVE,
        trial_ends_at=None,
        current_period_start=sample_sub.current_period_start,
        current_period_end=sample_sub.current_period_end,
        created_at=sample_sub.created_at,
    )
    mock_repo.update_seats.return_value = updated

    result = await service.add_seat(org_id)

    assert result.current_seats == 1
    mock_repo.update_seats.assert_called_once_with(org_id, 1)


@pytest.mark.asyncio
async def test_add_seat_limit_reached(service, mock_repo, org_id, sub_id):
    full_sub = OrgSubscription(
        id=sub_id,
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test",
        stripe_customer_id="cus_test",
        max_seats=20,
        current_seats=20,
        price_cents=100000,
        status=OrgSubscriptionStatus.ACTIVE,
        trial_ends_at=None,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
    )
    mock_repo.get_by_org.return_value = full_sub

    with pytest.raises(AppError, match="Seat limit reached"):
        await service.add_seat(org_id)


# --- remove_seat ---


@pytest.mark.asyncio
async def test_remove_seat_success(service, mock_repo, org_id, sub_id):
    sub_with_seats = OrgSubscription(
        id=sub_id,
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test",
        stripe_customer_id="cus_test",
        max_seats=20,
        current_seats=5,
        price_cents=100000,
        status=OrgSubscriptionStatus.ACTIVE,
        trial_ends_at=None,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
    )
    mock_repo.get_by_org.return_value = sub_with_seats
    updated = OrgSubscription(
        id=sub_id,
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test",
        stripe_customer_id="cus_test",
        max_seats=20,
        current_seats=4,
        price_cents=100000,
        status=OrgSubscriptionStatus.ACTIVE,
        trial_ends_at=None,
        current_period_start=sub_with_seats.current_period_start,
        current_period_end=sub_with_seats.current_period_end,
        created_at=sub_with_seats.created_at,
    )
    mock_repo.update_seats.return_value = updated

    result = await service.remove_seat(org_id)

    assert result.current_seats == 4
    mock_repo.update_seats.assert_called_once_with(org_id, 4)


@pytest.mark.asyncio
async def test_remove_seat_already_zero(service, mock_repo, org_id, sample_sub):
    mock_repo.get_by_org.return_value = sample_sub  # current_seats=0

    with pytest.raises(AppError, match="No seats to remove"):
        await service.remove_seat(org_id)


# --- cancel_subscription ---


@pytest.mark.asyncio
async def test_cancel_subscription_success(service, mock_repo, mock_stripe, org_id, sample_sub):
    mock_repo.get_by_org.return_value = sample_sub
    mock_stripe.cancel_subscription.return_value = {
        "id": "sub_test123",
        "status": "canceled",
    }
    canceled = OrgSubscription(
        id=sample_sub.id,
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test123",
        stripe_customer_id="cus_test123",
        max_seats=20,
        current_seats=0,
        price_cents=100000,
        status=OrgSubscriptionStatus.CANCELED,
        trial_ends_at=None,
        current_period_start=sample_sub.current_period_start,
        current_period_end=sample_sub.current_period_end,
        created_at=sample_sub.created_at,
    )
    mock_repo.update_status.return_value = canceled

    result = await service.cancel_subscription(org_id)

    assert result.status == OrgSubscriptionStatus.CANCELED
    mock_stripe.cancel_subscription.assert_called_once_with(
        "sub_test123", at_period_end=False,
    )
    mock_repo.update_status.assert_called_once_with(
        org_id, OrgSubscriptionStatus.CANCELED,
    )


@pytest.mark.asyncio
async def test_cancel_subscription_not_found(service, mock_repo, org_id):
    mock_repo.get_by_org.return_value = None

    with pytest.raises(NotFoundError, match="No subscription"):
        await service.cancel_subscription(org_id)


@pytest.mark.asyncio
async def test_cancel_already_canceled(service, mock_repo, org_id, sub_id):
    canceled = OrgSubscription(
        id=sub_id,
        organization_id=org_id,
        plan_tier=PlanTier.PILOT,
        stripe_subscription_id="sub_test",
        stripe_customer_id="cus_test",
        max_seats=20,
        current_seats=0,
        price_cents=100000,
        status=OrgSubscriptionStatus.CANCELED,
        trial_ends_at=None,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
    )
    mock_repo.get_by_org.return_value = canceled

    with pytest.raises(AppError, match="already canceled"):
        await service.cancel_subscription(org_id)


# --- handle_webhook ---


@pytest.mark.asyncio
async def test_webhook_invoice_paid(service, mock_repo, org_id, sample_sub):
    mock_repo.get_by_stripe_subscription_id.return_value = sample_sub
    mock_repo.update_status.return_value = sample_sub

    await service.handle_webhook(
        event_type="invoice.paid",
        stripe_subscription_id="sub_test123",
    )

    mock_repo.update_status.assert_called_once_with(
        org_id, OrgSubscriptionStatus.ACTIVE,
    )


@pytest.mark.asyncio
async def test_webhook_invoice_payment_failed(service, mock_repo, org_id, sample_sub):
    mock_repo.get_by_stripe_subscription_id.return_value = sample_sub
    mock_repo.update_status.return_value = sample_sub

    await service.handle_webhook(
        event_type="invoice.payment_failed",
        stripe_subscription_id="sub_test123",
    )

    mock_repo.update_status.assert_called_once_with(
        org_id, OrgSubscriptionStatus.PAST_DUE,
    )


@pytest.mark.asyncio
async def test_webhook_subscription_deleted(service, mock_repo, org_id, sample_sub):
    mock_repo.get_by_stripe_subscription_id.return_value = sample_sub
    mock_repo.update_status.return_value = sample_sub

    await service.handle_webhook(
        event_type="customer.subscription.deleted",
        stripe_subscription_id="sub_test123",
    )

    mock_repo.update_status.assert_called_once_with(
        org_id, OrgSubscriptionStatus.CANCELED,
    )


@pytest.mark.asyncio
async def test_webhook_unknown_subscription_ignored(service, mock_repo):
    mock_repo.get_by_stripe_subscription_id.return_value = None

    # Should not raise — idempotent
    await service.handle_webhook(
        event_type="invoice.paid",
        stripe_subscription_id="sub_unknown",
    )

    mock_repo.update_status.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_unhandled_event_type(service, mock_repo):
    # Should not raise for unknown event types
    await service.handle_webhook(
        event_type="some.unknown.event",
        stripe_subscription_id="sub_test",
    )

    mock_repo.get_by_stripe_subscription_id.assert_not_called()
