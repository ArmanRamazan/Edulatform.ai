from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from common.errors import ForbiddenError, NotFoundError
from app.domain.payment import Payment
from app.repositories.payment_repo import PaymentRepository
from app.repositories.earnings_repo import EarningsRepository


class PaymentService:
    def __init__(
        self,
        repo: PaymentRepository,
        earnings_repo: EarningsRepository | None = None,
    ) -> None:
        self._repo = repo
        self._earnings_repo = earnings_repo

    async def create(
        self,
        student_id: UUID,
        role: str,
        course_id: UUID,
        amount: Decimal,
    ) -> Payment:
        if role != "student":
            raise ForbiddenError("Only students can make payments")
        payment = await self._repo.create(student_id, course_id, amount)
        if self._earnings_repo is not None:
            await self._record_earning(
                course_id=course_id,
                payment_id=payment.id,
                gross_amount=amount,
            )
        return payment

    async def _record_earning(
        self,
        course_id: UUID,
        payment_id: UUID,
        gross_amount: Decimal,
    ) -> None:
        # teacher_id would come from course service in production;
        # for now we skip if earnings_repo is set but teacher_id unknown
        pass

    async def get(self, payment_id: UUID) -> Payment:
        payment = await self._repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError("Payment not found")
        return payment

    async def list_my(
        self, student_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Payment], int]:
        return await self._repo.list_by_student(student_id, limit, offset)
