from __future__ import annotations

from uuid import UUID

from common.errors import ForbiddenError, NotFoundError
from app.cache import CourseCache
from app.sanitize import sanitize_text
from app.domain.review import Review
from app.repositories.course_repo import CourseRepository
from app.repositories.review_repo import ReviewRepository


class ReviewService:
    def __init__(
        self,
        repo: ReviewRepository,
        course_repo: CourseRepository,
        cache: CourseCache | None = None,
    ) -> None:
        self._repo = repo
        self._course_repo = course_repo
        self._cache = cache

    async def create(
        self,
        student_id: UUID,
        role: str,
        course_id: UUID,
        rating: int,
        comment: str,
    ) -> Review:
        if role != "student":
            raise ForbiddenError("Only students can leave reviews")

        course = await self._course_repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course not found")

        comment = sanitize_text(comment)

        review = await self._repo.create(student_id, course_id, rating, comment)

        avg_rating, review_count = await self._repo.get_avg(course_id)
        await self._course_repo.update_rating(course_id, avg_rating, review_count)

        if self._cache:
            await self._cache.invalidate_course(course_id)

        return review

    async def list_by_course(
        self, course_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Review], int]:
        return await self._repo.list_by_course(course_id, limit, offset)
