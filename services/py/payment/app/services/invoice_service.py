from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from common.errors import ForbiddenError, NotFoundError
from app.domain.invoice import InvoiceData, generate_invoice_number
from app.adapters.invoice import InvoicePDFGenerator
from app.repositories.payment_repo import PaymentRepository


class InvoiceService:
    def __init__(
        self,
        payment_repo: PaymentRepository,
        pdf_generator: InvoicePDFGenerator,
    ) -> None:
        self._payment_repo = payment_repo
        self._pdf_generator = pdf_generator

    async def generate_invoice(
        self,
        user_id: UUID,
        payment_id: UUID,
        role: str,
        buyer_name: str,
        buyer_email: str,
        course_title: str,
        coupon_code: str | None = None,
        discount_amount: Decimal = Decimal("0"),
    ) -> tuple[bytes, str]:
        payment = await self._payment_repo.get_by_id(payment_id)
        if not payment:
            raise NotFoundError("Payment not found")

        if role != "admin" and payment.student_id != user_id:
            raise ForbiddenError("Access denied")

        original_price = payment.amount + discount_amount

        invoice_data = InvoiceData(
            invoice_number=generate_invoice_number(),
            payment_date=payment.created_at,
            buyer_name=buyer_name,
            buyer_email=buyer_email,
            course_title=course_title,
            original_price=original_price,
            discount_amount=discount_amount,
            final_price=payment.amount,
            coupon_code=coupon_code,
        )

        pdf_bytes = self._pdf_generator.generate_invoice(invoice_data)
        filename = f"invoice_{payment_id}.pdf"

        return pdf_bytes, filename
