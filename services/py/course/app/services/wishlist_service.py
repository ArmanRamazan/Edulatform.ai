from __future__ import annotations

from uuid import UUID

from common.errors import NotFoundError
from app.domain.wishlist import WishlistItem
from app.repositories.course_repo import CourseRepository
from app.repositories.wishlist_repo import WishlistRepository


class WishlistService:
    def __init__(
        self,
        repo: WishlistRepository,
        course_repo: CourseRepository,
    ) -> None:
        self._repo = repo
        self._course_repo = course_repo

    async def add_to_wishlist(self, user_id: UUID, course_id: UUID) -> WishlistItem:
        course = await self._course_repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course not found")

        return await self._repo.add(user_id, course_id)

    async def remove_from_wishlist(self, user_id: UUID, course_id: UUID) -> None:
        removed = await self._repo.remove(user_id, course_id)
        if not removed:
            raise NotFoundError("Course not in wishlist")

    async def get_my_wishlist(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[WishlistItem], int]:
        return await self._repo.get_by_user(user_id, limit, offset)

    async def is_in_wishlist(self, user_id: UUID, course_id: UUID) -> bool:
        return await self._repo.exists(user_id, course_id)
