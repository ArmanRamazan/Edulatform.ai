from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from common.errors import ForbiddenError
from app.domain.payment import (
    EarningResponse,
    EarningsSummary,
    EarningStatus,
    Payout,
    TeacherEarning,
)
from app.repositories.earnings_repo import EarningsRepository


class EarningsService:
    def __init__(self, repo: EarningsRepository) -> None:
        self._repo = repo

    async def get_summary(self, teacher_id: UUID, role: str) -> EarningsSummary:
        if role != "teacher":
            raise ForbiddenError("Only teachers can view earnings")

        earnings = await self._repo.get_earnings_by_teacher(teacher_id)

        total_gross = sum((e.gross_amount for e in earnings), Decimal("0"))
        total_net = sum((e.net_amount for e in earnings), Decimal("0"))
        total_pending = sum(
            (e.net_amount for e in earnings if e.status == EarningStatus.PENDING),
            Decimal("0"),
        )
        total_paid = sum(
            (e.net_amount for e in earnings if e.status == EarningStatus.PAID),
            Decimal("0"),
        )

        return EarningsSummary(
            total_gross=total_gross,
            total_net=total_net,
            total_pending=total_pending,
            total_paid=total_paid,
            earnings=[_to_earning_response(e) for e in earnings],
        )

    async def list_earnings(
        self, teacher_id: UUID, role: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[TeacherEarning], int]:
        if role != "teacher":
            raise ForbiddenError("Only teachers can view earnings")
        return await self._repo.list_earnings(teacher_id, limit, offset)

    async def request_payout(
        self, teacher_id: UUID, role: str, amount: Decimal
    ) -> Payout:
        if role != "teacher":
            raise ForbiddenError("Only teachers can request payouts")
        return await self._repo.create_payout(teacher_id, amount)

    async def list_payouts(
        self, teacher_id: UUID, role: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[Payout], int]:
        if role != "teacher":
            raise ForbiddenError("Only teachers can view payouts")
        return await self._repo.list_payouts(teacher_id, limit, offset)


def _to_earning_response(e: TeacherEarning) -> EarningResponse:
    return EarningResponse(
        id=e.id,
        teacher_id=e.teacher_id,
        course_id=e.course_id,
        payment_id=e.payment_id,
        gross_amount=e.gross_amount,
        commission_rate=e.commission_rate,
        net_amount=e.net_amount,
        status=e.status,
        created_at=e.created_at,
    )
