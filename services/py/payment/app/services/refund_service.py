from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from common.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.domain.payment import PaymentStatus
from app.domain.refund import Refund, RefundStatus
from app.repositories.payment_repo import PaymentRepository
from app.repositories.refund_repo import RefundRepository

REFUND_WINDOW_DAYS = 14


class RefundService:
    def __init__(
        self,
        refund_repo: RefundRepository,
        payment_repo: PaymentRepository,
    ) -> None:
        self._refund_repo = refund_repo
        self._payment_repo = payment_repo

    async def request_refund(
        self,
        user_id: UUID,
        payment_id: UUID,
        reason: str,
    ) -> Refund:
        payment = await self._payment_repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError("Payment not found")

        if payment.student_id != user_id:
            raise ForbiddenError(
                "You can only request refunds for your own payments"
            )

        if payment.status != PaymentStatus.COMPLETED:
            raise AppError(
                "Refunds can only be requested for completed payments",
                status_code=400,
            )

        existing = await self._refund_repo.get_by_payment_id(payment_id)
        if existing:
            raise ConflictError(
                "A refund has already been requested for this payment"
            )

        cutoff = datetime.now(timezone.utc) - timedelta(days=REFUND_WINDOW_DAYS)
        if payment.created_at < cutoff:
            raise AppError(
                "Refunds can only be requested within 14-day window",
                status_code=400,
            )

        return await self._refund_repo.create_refund(
            payment_id=payment_id,
            user_id=user_id,
            reason=reason,
            amount=payment.amount,
        )

    async def get_my_refunds(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Refund], int]:
        return await self._refund_repo.get_user_refunds(user_id, limit, offset)

    async def list_refunds(
        self,
        role: str,
        status_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Refund], int]:
        if role != "admin":
            raise ForbiddenError("Only admins can list all refunds")
        return await self._refund_repo.list_all_refunds(
            status_filter, limit, offset,
        )

    async def approve_refund(
        self,
        admin_id: UUID,
        refund_id: UUID,
        role: str,
    ) -> Refund:
        if role != "admin":
            raise ForbiddenError("Only admins can approve refunds")

        refund = await self._refund_repo.get_refund(refund_id)
        if not refund:
            raise NotFoundError("Refund not found")

        if refund.status != RefundStatus.REQUESTED:
            raise AppError(
                "Refund has already been processed", status_code=400,
            )

        now = datetime.now(timezone.utc)
        updated = await self._refund_repo.update_status(
            refund_id=refund_id,
            status=RefundStatus.APPROVED,
            processed_at=now,
        )

        await self._payment_repo.update_status(
            refund.payment_id, PaymentStatus.REFUNDED,
        )

        return updated

    async def reject_refund(
        self,
        admin_id: UUID,
        refund_id: UUID,
        role: str,
        reason: str,
    ) -> Refund:
        if role != "admin":
            raise ForbiddenError("Only admins can reject refunds")

        refund = await self._refund_repo.get_refund(refund_id)
        if not refund:
            raise NotFoundError("Refund not found")

        if refund.status != RefundStatus.REQUESTED:
            raise AppError(
                "Refund has already been processed", status_code=400,
            )

        now = datetime.now(timezone.utc)
        return await self._refund_repo.update_status(
            refund_id=refund_id,
            status=RefundStatus.REJECTED,
            admin_note=reason,
            processed_at=now,
        )
