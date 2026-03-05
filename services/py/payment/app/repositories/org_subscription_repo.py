from __future__ import annotations

from datetime import datetime
from uuid import UUID

import asyncpg

from app.domain.org_subscription import (
    OrgSubscription,
    OrgSubscriptionStatus,
    PlanTier,
)


class OrgSubscriptionRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        organization_id: UUID,
        plan_tier: PlanTier,
        stripe_subscription_id: str | None,
        stripe_customer_id: str | None,
        max_seats: int,
        price_cents: int,
        status: OrgSubscriptionStatus,
        current_period_start: datetime | None,
        current_period_end: datetime | None,
    ) -> OrgSubscription:
        row = await self._pool.fetchrow(
            """
            INSERT INTO org_subscriptions
                (organization_id, plan_tier, stripe_subscription_id, stripe_customer_id,
                 max_seats, price_cents, status, current_period_start, current_period_end)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
            """,
            organization_id,
            str(plan_tier),
            stripe_subscription_id,
            stripe_customer_id,
            max_seats,
            price_cents,
            str(status),
            current_period_start,
            current_period_end,
        )
        return self._to_entity(row)

    async def get_by_org(self, organization_id: UUID) -> OrgSubscription | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM org_subscriptions WHERE organization_id = $1",
            organization_id,
        )
        return self._to_entity(row) if row else None

    async def get_by_stripe_subscription_id(
        self, stripe_subscription_id: str,
    ) -> OrgSubscription | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM org_subscriptions WHERE stripe_subscription_id = $1",
            stripe_subscription_id,
        )
        return self._to_entity(row) if row else None

    async def update_seats(
        self, organization_id: UUID, new_seats: int,
    ) -> OrgSubscription:
        row = await self._pool.fetchrow(
            """
            UPDATE org_subscriptions
            SET current_seats = $2
            WHERE organization_id = $1
            RETURNING *
            """,
            organization_id,
            new_seats,
        )
        return self._to_entity(row)

    async def update_status(
        self, organization_id: UUID, status: OrgSubscriptionStatus,
    ) -> OrgSubscription:
        row = await self._pool.fetchrow(
            """
            UPDATE org_subscriptions
            SET status = $2
            WHERE organization_id = $1
            RETURNING *
            """,
            organization_id,
            str(status),
        )
        return self._to_entity(row)

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> OrgSubscription:
        return OrgSubscription(
            id=row["id"],
            organization_id=row["organization_id"],
            plan_tier=PlanTier(row["plan_tier"]),
            stripe_subscription_id=row.get("stripe_subscription_id"),
            stripe_customer_id=row.get("stripe_customer_id"),
            max_seats=row["max_seats"],
            current_seats=row["current_seats"],
            price_cents=row["price_cents"],
            status=OrgSubscriptionStatus(row["status"]),
            trial_ends_at=row.get("trial_ends_at"),
            current_period_start=row.get("current_period_start"),
            current_period_end=row.get("current_period_end"),
            created_at=row["created_at"],
        )
