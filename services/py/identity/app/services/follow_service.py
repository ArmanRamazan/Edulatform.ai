from uuid import UUID

from common.errors import AppError, NotFoundError
from app.domain.follow import Follow, FollowStats
from app.repositories.follow_repo import FollowRepository
from app.repositories.user_repo import UserRepository


class FollowService:
    def __init__(self, follow_repo: FollowRepository, user_repo: UserRepository) -> None:
        self._follow_repo = follow_repo
        self._user_repo = user_repo

    async def follow_user(self, follower_id: UUID, following_id: UUID) -> Follow:
        if follower_id == following_id:
            raise AppError("Cannot follow yourself")
        user = await self._user_repo.get_by_id(following_id)
        if not user:
            raise NotFoundError("User not found")
        return await self._follow_repo.follow(follower_id, following_id)

    async def unfollow_user(self, follower_id: UUID, following_id: UUID) -> None:
        removed = await self._follow_repo.unfollow(follower_id, following_id)
        if not removed:
            raise NotFoundError("Not following this user")

    async def get_followers(self, user_id: UUID, limit: int, offset: int) -> tuple[list[Follow], int]:
        return await self._follow_repo.get_followers(user_id, limit, offset)

    async def get_following(self, user_id: UUID, limit: int, offset: int) -> tuple[list[Follow], int]:
        return await self._follow_repo.get_following(user_id, limit, offset)

    async def get_follow_counts(self, user_id: UUID) -> FollowStats:
        followers = await self._follow_repo.count_followers(user_id)
        following = await self._follow_repo.count_following(user_id)
        return FollowStats(followers_count=followers, following_count=following)
