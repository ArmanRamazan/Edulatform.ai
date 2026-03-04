from uuid import UUID

from common.errors import NotFoundError
from app.domain.user import PublicProfile
from app.repositories.user_repo import UserRepository


class ProfileService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def get_public_profile(self, user_id: UUID) -> PublicProfile:
        profile = await self._repo.get_public_profile(user_id)
        if not profile:
            raise NotFoundError("User not found")
        return profile

    async def get_user_stats(self, user_id: UUID) -> dict:
        profile = await self._repo.get_public_profile(user_id)
        if not profile:
            raise NotFoundError("User not found")
        return {
            "name": profile.name,
            "role": profile.role,
            "is_verified": profile.is_verified,
            "member_since": profile.created_at,
        }

    async def update_visibility(self, user_id: UUID, is_public: bool) -> None:
        await self._repo.update_profile_visibility(user_id, is_public)
