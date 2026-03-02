from datetime import datetime, timedelta, timezone

from common.errors import ForbiddenError
from app.repositories.cache import AICache

PLAN_LIMITS: dict[str, int] = {
    "free": 10,
    "student": 100,
    "pro": -1,
}

_UNLIMITED_REMAINING = 999999


class CreditService:
    def __init__(self, cache: AICache) -> None:
        self._cache = cache

    def get_limit(self, tier: str) -> int:
        return PLAN_LIMITS.get(tier, PLAN_LIMITS["free"])

    async def get_used(self, user_id: str) -> int:
        return await self._cache.get_credits_used(user_id)

    async def check_and_consume(self, user_id: str, tier: str) -> int:
        limit = self.get_limit(tier)

        if limit != -1:
            used = await self._cache.get_credits_used(user_id)
            if used >= limit:
                raise ForbiddenError("AI credit limit reached. Upgrade your plan.")

        new_count = await self._cache.increment_credits(user_id)

        if limit == -1:
            return _UNLIMITED_REMAINING
        return max(0, limit - new_count)

    async def get_status(self, user_id: str, tier: str) -> dict:
        used = await self._cache.get_credits_used(user_id)
        limit = self.get_limit(tier)

        if limit == -1:
            remaining = _UNLIMITED_REMAINING
        else:
            remaining = max(0, limit - used)

        now = datetime.now(timezone.utc)
        reset_at = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        return {
            "used": used,
            "limit": limit,
            "remaining": remaining,
            "reset_at": reset_at.isoformat(),
            "tier": tier,
        }
