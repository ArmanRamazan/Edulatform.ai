from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import asyncpg

from app.domain.subscription import (
    SubscriptionPlan,
    SubscriptionStatus,
    UserSubscription,
)


class SubscriptionRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_plan_by_name(self, name: str) -> SubscriptionPlan | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM subscription_plans WHERE name = $1",
            name,
        )
        return self._to_plan_entity(row) if row else None

    async def get_plan_by_id(self, plan_id: UUID) -> SubscriptionPlan | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM subscription_plans WHERE id = $1",
            plan_id,
        )
        return self._to_plan_entity(row) if row else None

    async def list_plans(self) -> list[SubscriptionPlan]:
        rows = await self._pool.fetch(
            "SELECT * FROM subscription_plans ORDER BY price_monthly",
        )
        return [self._to_plan_entity(r) for r in rows]

    async def get_user_subscription(self, user_id: UUID) -> UserSubscription | None:
        row = await self._pool.fetchrow(
            """
            SELECT us.*, sp.name AS plan_name
            FROM user_subscriptions us
            JOIN subscription_plans sp ON sp.id = us.plan_id
            WHERE us.user_id = $1
            """,
            user_id,
        )
        return self._to_subscription_entity(row) if row else None

    async def create_user_subscription(
        self,
        user_id: UUID,
        plan_id: UUID,
        stripe_subscription_id: str | None,
        stripe_customer_id: str | None,
        status: SubscriptionStatus,
        period_start: datetime | None,
        period_end: datetime | None,
    ) -> UserSubscription:
        row = await self._pool.fetchrow(
            """
            INSERT INTO user_subscriptions
                (user_id, plan_id, stripe_subscription_id, stripe_customer_id,
                 status, current_period_start, current_period_end)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *, (SELECT name FROM subscription_plans WHERE id = $2) AS plan_name
            """,
            user_id,
            plan_id,
            stripe_subscription_id,
            stripe_customer_id,
            str(status),
            period_start,
            period_end,
        )
        return self._to_subscription_entity(row)

    async def update_user_subscription(
        self,
        user_id: UUID,
        **fields: object,
    ) -> UserSubscription:
        allowed = {
            "status", "cancel_at_period_end",
            "current_period_start", "current_period_end",
            "stripe_subscription_id", "stripe_customer_id",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        set_clauses = ", ".join(
            f"{k} = ${i + 2}" for i, k in enumerate(updates)
        )
        set_clauses += f", updated_at = now()"
        values = [user_id, *updates.values()]

        row = await self._pool.fetchrow(
            f"""
            UPDATE user_subscriptions
            SET {set_clauses}
            WHERE user_id = $1
            RETURNING *, (SELECT name FROM subscription_plans WHERE id = plan_id) AS plan_name
            """,
            *values,
        )
        return self._to_subscription_entity(row)

    @staticmethod
    def _to_plan_entity(row: asyncpg.Record) -> SubscriptionPlan:
        features = row["features"]
        if isinstance(features, str):
            features = json.loads(features)
        return SubscriptionPlan(
            id=row["id"],
            name=row["name"],
            stripe_price_id=row.get("stripe_price_id"),
            price_monthly=row["price_monthly"],
            price_yearly=row.get("price_yearly"),
            ai_credits_daily=row["ai_credits_daily"],
            features=features,
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_subscription_entity(row: asyncpg.Record) -> UserSubscription:
        return UserSubscription(
            id=row["id"],
            user_id=row["user_id"],
            plan_id=row["plan_id"],
            plan_name=row["plan_name"],
            stripe_subscription_id=row.get("stripe_subscription_id"),
            stripe_customer_id=row.get("stripe_customer_id"),
            status=SubscriptionStatus(row["status"]),
            current_period_start=row.get("current_period_start"),
            current_period_end=row.get("current_period_end"),
            cancel_at_period_end=row.get("cancel_at_period_end", False),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
