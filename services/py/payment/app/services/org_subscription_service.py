from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from common.errors import AppError, NotFoundError, ConflictError
from app.domain.org_subscription import (
    OrgSubscription,
    OrgSubscriptionStatus,
    PlanTier,
    PLAN_TIERS,
)
from app.repositories.org_subscription_repo import OrgSubscriptionRepository
from app.repositories.stripe_client import StripeClient


_HANDLED_WEBHOOK_EVENTS = frozenset({
    "invoice.paid",
    "invoice.payment_failed",
    "customer.subscription.deleted",
})


class OrgSubscriptionService:
    def __init__(
        self,
        repo: OrgSubscriptionRepository,
        stripe_client: StripeClient,
    ) -> None:
        self._repo = repo
        self._stripe = stripe_client

    async def create_subscription(
        self,
        organization_id: UUID,
        plan_tier: str,
        payment_method_id: str,
        org_email: str,
        org_name: str,
    ) -> OrgSubscription:
        existing = await self._repo.get_by_org(organization_id)
        if existing is not None:
            raise ConflictError("Organization already has an active subscription")

        try:
            tier = PlanTier(plan_tier)
        except ValueError:
            raise AppError(
                f"Invalid plan tier: {plan_tier}. Must be one of: {', '.join(t.value for t in PlanTier)}",
                status_code=422,
            )

        tier_config = PLAN_TIERS[tier]

        customer_id = await self._stripe.create_customer(
            email=org_email, name=org_name,
        )
        stripe_sub = await self._stripe.create_subscription(
            customer_id=customer_id,
            price_id=tier_config["stripe_price_id"],
            payment_method_id=payment_method_id,
        )

        period_start = datetime.fromtimestamp(
            stripe_sub["current_period_start"], tz=timezone.utc,
        )
        period_end = datetime.fromtimestamp(
            stripe_sub["current_period_end"], tz=timezone.utc,
        )

        return await self._repo.create(
            organization_id=organization_id,
            plan_tier=tier,
            stripe_subscription_id=stripe_sub["id"],
            stripe_customer_id=customer_id,
            max_seats=tier_config["max_seats"],
            price_cents=tier_config["price_cents"],
            status=OrgSubscriptionStatus.ACTIVE,
            current_period_start=period_start,
            current_period_end=period_end,
        )

    async def get_subscription(self, organization_id: UUID) -> OrgSubscription:
        sub = await self._repo.get_by_org(organization_id)
        if sub is None:
            raise NotFoundError("No subscription found for this organization")
        return sub

    async def check_seat_limit(self, organization_id: UUID) -> bool:
        sub = await self._repo.get_by_org(organization_id)
        if sub is None:
            raise NotFoundError("No subscription found for this organization")
        if sub.status != OrgSubscriptionStatus.ACTIVE:
            raise AppError("Subscription is not active", status_code=400)
        return sub.current_seats < sub.max_seats

    async def add_seat(self, organization_id: UUID) -> OrgSubscription:
        sub = await self._repo.get_by_org(organization_id)
        if sub is None:
            raise NotFoundError("No subscription found for this organization")
        if sub.status != OrgSubscriptionStatus.ACTIVE:
            raise AppError("Subscription is not active", status_code=400)
        if sub.current_seats >= sub.max_seats:
            raise AppError("Seat limit reached. Upgrade your plan.", status_code=400)
        return await self._repo.update_seats(organization_id, sub.current_seats + 1)

    async def remove_seat(self, organization_id: UUID) -> OrgSubscription:
        sub = await self._repo.get_by_org(organization_id)
        if sub is None:
            raise NotFoundError("No subscription found for this organization")
        if sub.current_seats <= 0:
            raise AppError("No seats to remove", status_code=400)
        return await self._repo.update_seats(organization_id, sub.current_seats - 1)

    async def cancel_subscription(self, organization_id: UUID) -> OrgSubscription:
        sub = await self._repo.get_by_org(organization_id)
        if sub is None:
            raise NotFoundError("No subscription found for this organization")
        if sub.status == OrgSubscriptionStatus.CANCELED:
            raise AppError("Subscription is already canceled", status_code=400)

        if sub.stripe_subscription_id:
            await self._stripe.cancel_subscription(
                sub.stripe_subscription_id, at_period_end=False,
            )

        return await self._repo.update_status(
            organization_id, OrgSubscriptionStatus.CANCELED,
        )

    async def handle_webhook(
        self,
        event_type: str,
        stripe_subscription_id: str,
    ) -> None:
        if event_type not in _HANDLED_WEBHOOK_EVENTS:
            return

        sub = await self._repo.get_by_stripe_subscription_id(stripe_subscription_id)
        if sub is None:
            return  # Idempotent: unknown subscription, ignore

        status_map = {
            "invoice.paid": OrgSubscriptionStatus.ACTIVE,
            "invoice.payment_failed": OrgSubscriptionStatus.PAST_DUE,
            "customer.subscription.deleted": OrgSubscriptionStatus.CANCELED,
        }

        new_status = status_map[event_type]
        await self._repo.update_status(sub.organization_id, new_status)
