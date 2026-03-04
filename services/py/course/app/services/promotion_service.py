from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from common.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.domain.promotion import ActivePromotion, CoursePromotion
from app.repositories.course_repo import CourseRepository
from app.repositories.promotion_repo import PromotionRepository


class PromotionService:
    def __init__(
        self,
        repo: PromotionRepository,
        course_repo: CourseRepository,
    ) -> None:
        self._repo = repo
        self._course_repo = course_repo

    async def create_promotion(
        self,
        teacher_id: UUID,
        course_id: UUID,
        promo_price: Decimal,
        starts_at: datetime,
        ends_at: datetime,
    ) -> CoursePromotion:
        course = await self._course_repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course not found")
        if course.teacher_id != teacher_id:
            raise ForbiddenError("Only the course owner can create promotions")
        if course.is_free or course.price is None:
            raise AppError("Cannot create promotion for a free course")
        if ends_at <= starts_at:
            raise AppError("ends_at must be after starts_at")
        if promo_price >= course.price:
            raise AppError(f"Promo price must be less than original price ({course.price})")

        existing = await self._repo.get_active_promotion(course_id)
        if existing:
            raise ConflictError("Course already has an active promotion")

        return await self._repo.create_promotion(
            course_id=course_id,
            original_price=course.price,
            promo_price=promo_price,
            starts_at=starts_at,
            ends_at=ends_at,
            created_by=teacher_id,
        )

    async def get_active_promotion(self, course_id: UUID) -> ActivePromotion | None:
        promo = await self._repo.get_active_promotion(course_id)
        if not promo:
            return None
        return ActivePromotion(promo_price=promo.promo_price, ends_at=promo.ends_at)

    async def get_active_promotions_batch(
        self, course_ids: list[UUID],
    ) -> dict[UUID, ActivePromotion]:
        promos = await self._repo.get_active_promotions_batch(course_ids)
        return {
            cid: ActivePromotion(promo_price=p.promo_price, ends_at=p.ends_at)
            for cid, p in promos.items()
        }

    async def get_course_promotions(
        self, teacher_id: UUID, course_id: UUID,
    ) -> list[CoursePromotion]:
        course = await self._course_repo.get_by_id(course_id)
        if not course:
            raise NotFoundError("Course not found")
        if course.teacher_id != teacher_id:
            raise ForbiddenError("Only the course owner can view all promotions")
        return await self._repo.get_course_promotions(course_id)

    async def delete_promotion(
        self, teacher_id: UUID, promotion_id: UUID,
    ) -> None:
        promo = await self._repo.get_promotion(promotion_id)
        if not promo:
            raise NotFoundError("Promotion not found")
        course = await self._course_repo.get_by_id(promo.course_id)
        if not course:
            raise NotFoundError("Course not found")
        if course.teacher_id != teacher_id:
            raise ForbiddenError("Only the course owner can delete promotions")
        await self._repo.delete_promotion(promotion_id)
