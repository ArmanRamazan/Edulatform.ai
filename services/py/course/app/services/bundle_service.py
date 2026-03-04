from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from common.errors import AppError, ForbiddenError, NotFoundError
from app.sanitize import sanitize_text, sanitize_html
from app.domain.bundle import BundleWithCourses, CourseBundle
from app.repositories.bundle_repo import BundleRepository
from app.repositories.course_repo import CourseRepository


class BundleService:
    def __init__(
        self,
        repo: BundleRepository,
        course_repo: CourseRepository,
    ) -> None:
        self._repo = repo
        self._course_repo = course_repo

    async def create_bundle(
        self,
        teacher_id: UUID,
        role: str,
        is_verified: bool,
        title: str,
        description: str,
        price: Decimal,
        discount_percent: int,
        course_ids: list[UUID],
    ) -> BundleWithCourses:
        if role != "teacher":
            raise ForbiddenError("Only teachers can create bundles")
        if not is_verified:
            raise ForbiddenError("Only verified teachers can create bundles")
        if price <= 0:
            raise AppError("Price must be greater than 0")
        if not 1 <= discount_percent <= 99:
            raise AppError("Discount must be between 1 and 99")
        if not 2 <= len(course_ids) <= 10:
            raise AppError("Bundle must contain between 2 and 10 courses")

        for cid in course_ids:
            course = await self._course_repo.get_by_id(cid)
            if not course:
                raise NotFoundError(f"Course {cid} not found")
            if course.teacher_id != teacher_id:
                raise ForbiddenError("All courses in a bundle must belong to you")

        title = sanitize_text(title)
        description = sanitize_html(description)

        return await self._repo.create_bundle_with_courses(
            teacher_id=teacher_id,
            title=title,
            description=description,
            price=price,
            discount_percent=discount_percent,
            course_ids=course_ids,
        )

    async def get_bundle(self, bundle_id: UUID) -> BundleWithCourses:
        bwc = await self._repo.get_bundle_with_courses(bundle_id)
        if not bwc:
            raise NotFoundError("Bundle not found")
        return bwc

    async def list_bundles(
        self, limit: int = 20, offset: int = 0, teacher_id: UUID | None = None,
    ) -> tuple[list[CourseBundle], int]:
        return await self._repo.list_bundles(limit, offset, teacher_id)

    async def update_bundle(
        self,
        teacher_id: UUID,
        bundle_id: UUID,
        title: str | None = None,
        description: str | None = None,
        price: Decimal | None = None,
        discount_percent: int | None = None,
    ) -> BundleWithCourses:
        bundle = await self._repo.get_bundle(bundle_id)
        if not bundle:
            raise NotFoundError("Bundle not found")
        if bundle.teacher_id != teacher_id:
            raise ForbiddenError("Only the bundle owner can update this bundle")

        fields: dict[str, object] = {}
        if title is not None:
            fields["title"] = sanitize_text(title)
        if description is not None:
            fields["description"] = sanitize_html(description)
        if price is not None:
            if price <= 0:
                raise AppError("Price must be greater than 0")
            fields["price"] = price
        if discount_percent is not None:
            if not 1 <= discount_percent <= 99:
                raise AppError("Discount must be between 1 and 99")
            fields["discount_percent"] = discount_percent

        if fields:
            await self._repo.update_bundle(bundle_id, **fields)
        bwc = await self._repo.get_bundle_with_courses(bundle_id)
        if not bwc:
            raise NotFoundError("Bundle not found")
        return bwc

    async def delete_bundle(self, teacher_id: UUID, bundle_id: UUID) -> None:
        bundle = await self._repo.get_bundle(bundle_id)
        if not bundle:
            raise NotFoundError("Bundle not found")
        if bundle.teacher_id != teacher_id:
            raise ForbiddenError("Only the bundle owner can delete this bundle")
        await self._repo.delete_bundle(bundle_id)
