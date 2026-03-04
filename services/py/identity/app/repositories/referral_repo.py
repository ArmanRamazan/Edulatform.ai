from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.referral import Referral, ReferralStats


class ReferralRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_referral(self, referrer_id: UUID, referee_id: UUID, referral_code: str) -> Referral:
        row = await self._pool.fetchrow(
            """
            INSERT INTO referrals (referrer_id, referee_id, referral_code)
            VALUES ($1, $2, $3)
            RETURNING id, referrer_id, referee_id, referral_code, status,
                      reward_type, created_at, completed_at
            """,
            referrer_id,
            referee_id,
            referral_code,
        )
        return self._to_entity(row)

    async def get_referral_by_referee(self, referee_id: UUID) -> Referral | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, referrer_id, referee_id, referral_code, status,
                   reward_type, created_at, completed_at
            FROM referrals WHERE referee_id = $1
            """,
            referee_id,
        )
        return self._to_entity(row) if row else None

    async def get_referrer_by_code(self, referral_code: str) -> UUID | None:
        val = await self._pool.fetchval(
            "SELECT id FROM users WHERE referral_code = $1",
            referral_code,
        )
        return val

    async def complete_referral(self, referee_id: UUID) -> Referral | None:
        row = await self._pool.fetchrow(
            """
            UPDATE referrals
            SET status = 'completed', reward_type = 'credit', completed_at = now()
            WHERE referee_id = $1 AND status = 'pending'
            RETURNING id, referrer_id, referee_id, referral_code, status,
                      reward_type, created_at, completed_at
            """,
            referee_id,
        )
        return self._to_entity(row) if row else None

    async def get_referral_stats(self, user_id: UUID) -> ReferralStats:
        row = await self._pool.fetchrow(
            """
            SELECT
                COALESCE(u.referral_code, '') AS referral_code,
                COUNT(r.id) AS invited_count,
                COUNT(r.id) FILTER (WHERE r.status = 'completed') AS completed_count,
                COUNT(r.id) FILTER (WHERE r.reward_type IS NOT NULL) AS rewards_earned
            FROM users u
            LEFT JOIN referrals r ON r.referrer_id = u.id
            WHERE u.id = $1
            GROUP BY u.referral_code
            """,
            user_id,
        )
        if not row:
            return ReferralStats(referral_code="", invited_count=0, completed_count=0, rewards_earned=0)
        return ReferralStats(
            referral_code=row["referral_code"],
            invited_count=row["invited_count"],
            completed_count=row["completed_count"],
            rewards_earned=row["rewards_earned"],
        )

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Referral:
        return Referral(
            id=row["id"],
            referrer_id=row["referrer_id"],
            referee_id=row["referee_id"],
            referral_code=row["referral_code"],
            status=row["status"],
            reward_type=row["reward_type"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )
