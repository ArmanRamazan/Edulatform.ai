from __future__ import annotations

from uuid import UUID

import structlog

from common.errors import AppError

logger = structlog.get_logger()


class MockStripeService:
    """Mock Stripe implementation used when STRIPE_SECRET_KEY is not configured.

    Provides the same duck-type interface as StripeClient so it can be used
    transparently by OrgSubscriptionService. All methods log 'stripe_mock_mode'
    and return deterministic fixture data — no real network calls are made.
    """

    # --- High-level demo methods ---

    async def get_org_subscription(self, org_id: UUID) -> dict:
        logger.info("stripe_mock_mode")
        return {
            "id": "sub_mock_demo",
            "org_id": org_id,
            "plan": "enterprise",
            "status": "active",
            "current_seats": 10,
            "max_seats": 50,
            "price_cents": 100000,
            "currency": "usd",
            "current_period_start": "2026-01-01",
            "current_period_end": "2026-12-31",
        }

    async def get_user_subscription(self, user_id: UUID) -> dict:
        logger.info("stripe_mock_mode")
        return {
            "id": "sub_mock_user_demo",
            "user_id": user_id,
            "plan": "pro",
            "status": "active",
            "current_period_start": "2026-01-01",
            "current_period_end": "2026-12-31",
        }

    async def create_payment(self, data: dict) -> dict:
        logger.info("stripe_mock_mode")
        return {
            "id": "pay_mock_demo",
            "status": "succeeded",
            "amount": data.get("amount", 0),
            "currency": data.get("currency", "usd"),
        }

    # --- StripeClient-compatible methods (duck-type interface) ---

    async def create_customer(self, email: str, name: str) -> str:
        logger.info("stripe_mock_mode")
        return "cus_mock_demo"

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        payment_method_id: str,
    ) -> dict:
        logger.info("stripe_mock_mode")
        return {
            "id": "sub_mock_demo",
            "status": "active",
            # Unix timestamps: 2026-01-01 and 2026-12-31
            "current_period_start": 1735689600,
            "current_period_end": 1767225600,
        }

    async def cancel_subscription(
        self,
        stripe_subscription_id: str,
        at_period_end: bool = True,
    ) -> dict:
        logger.info("stripe_mock_mode")
        return {
            "id": stripe_subscription_id,
            "status": "canceled",
            "cancel_at_period_end": at_period_end,
        }

    async def construct_webhook_event(
        self,
        payload: bytes,
        sig_header: str,
        secret: str,
    ) -> dict:
        logger.info("stripe_mock_mode")
        raise AppError("Webhooks not supported in mock mode", status_code=400)


def create_stripe_client(settings: object) -> MockStripeService:
    """Return a StripeClient when a key is configured, MockStripeService otherwise.

    This is the single place where the mock/real decision is made.
    OrgSubscriptionService receives whichever is returned without knowing the difference.
    """
    from app.repositories.stripe_client import StripeClient  # local import avoids circular dep

    stripe_key: str = getattr(settings, "stripe_secret_key", "")
    if stripe_key:
        return StripeClient(stripe_key)  # type: ignore[return-value]
    logger.info("stripe_mock_mode", reason="STRIPE_SECRET_KEY not set — using MockStripeService")
    return MockStripeService()
