from __future__ import annotations

from uuid import UUID

from common.errors import AppError, ConflictError, NotFoundError
from app.domain.referral import Referral, ReferralStats, generate_referral_code
from app.repositories.referral_repo import ReferralRepository
from app.repositories.user_repo import UserRepository


class ReferralService:
    def __init__(self, referral_repo: ReferralRepository, user_repo: UserRepository) -> None:
        self._referral_repo = referral_repo
        self._user_repo = user_repo

    async def apply_referral_code(self, referee_id: UUID, referral_code: str) -> Referral:
        referrer_id = await self._referral_repo.get_referrer_by_code(referral_code)
        if not referrer_id:
            raise NotFoundError("Invalid referral code")

        if referrer_id == referee_id:
            raise AppError("Cannot refer yourself")

        existing = await self._referral_repo.get_referral_by_referee(referee_id)
        if existing:
            raise ConflictError("Already referred")

        return await self._referral_repo.create_referral(referrer_id, referee_id, referral_code)

    async def complete_referral(self, referee_id: UUID) -> Referral:
        result = await self._referral_repo.complete_referral(referee_id)
        if not result:
            raise NotFoundError("No pending referral")
        return result

    async def get_my_referral_info(self, user_id: UUID) -> ReferralStats:
        code = await self._user_repo.get_referral_code(user_id)
        if not code:
            code = await self.generate_referral_code(user_id)
        return await self._referral_repo.get_referral_stats(user_id)

    async def generate_referral_code(self, user_id: UUID) -> str:
        existing = await self._user_repo.get_referral_code(user_id)
        if existing:
            return existing
        code = generate_referral_code()
        return await self._user_repo.set_referral_code(user_id, code)
