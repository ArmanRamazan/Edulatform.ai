from __future__ import annotations

import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog

from common.errors import AppError, NotFoundError
from app.domain.gift import GiftPurchase, GiftStatus
from app.repositories.gift_repo import GiftRepository
from app.repositories.payment_repo import PaymentRepository

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GIFT_CODE_CHARS = string.ascii_uppercase + string.digits
GIFT_EXPIRY_DAYS = 90

logger = structlog.get_logger()


def _generate_gift_code() -> str:
    part1 = "".join(secrets.choice(GIFT_CODE_CHARS) for _ in range(4))
    part2 = "".join(secrets.choice(GIFT_CODE_CHARS) for _ in range(4))
    return f"GIFT-{part1}-{part2}"


class GiftService:
    def __init__(
        self,
        gift_repo: GiftRepository,
        payment_repo: PaymentRepository,
    ) -> None:
        self._gift_repo = gift_repo
        self._payment_repo = payment_repo

    async def purchase_gift(
        self,
        buyer_id: UUID,
        course_id: UUID,
        recipient_email: str,
        message: str | None = None,
    ) -> GiftPurchase:
        if not EMAIL_REGEX.match(recipient_email):
            raise AppError("Invalid email format", status_code=422)

        if message and len(message) > 500:
            raise AppError("Message cannot exceed 500 characters", status_code=422)

        # Create payment (mock — always completed, same as normal purchase)
        payment = await self._payment_repo.create(
            student_id=buyer_id,
            course_id=course_id,
            amount=0,  # Price would come from course service in real system
        )

        gift_code = _generate_gift_code()
        expires_at = datetime.now(timezone.utc) + timedelta(days=GIFT_EXPIRY_DAYS)

        gift = await self._gift_repo.create_gift(
            buyer_id=buyer_id,
            recipient_email=recipient_email,
            course_id=course_id,
            payment_id=payment.id,
            gift_code=gift_code,
            message=message,
            expires_at=expires_at,
        )

        logger.info(
            "gift_purchased",
            gift_code=gift_code,
            buyer_id=str(buyer_id),
            recipient_email=recipient_email,
        )

        return gift

    async def get_my_sent_gifts(
        self,
        buyer_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[GiftPurchase], int]:
        return await self._gift_repo.get_sent_gifts(buyer_id, limit, offset)

    async def redeem_gift(
        self,
        user_id: UUID,
        gift_code: str,
    ) -> GiftPurchase:
        gift = await self._gift_repo.get_gift_by_code(gift_code)
        if not gift:
            raise NotFoundError("Gift not found")

        if gift.status != GiftStatus.PURCHASED:
            raise AppError("Gift has already been redeemed", status_code=400)

        if gift.expires_at < datetime.now(timezone.utc):
            raise AppError("Gift has expired", status_code=400)

        redeemed = await self._gift_repo.redeem_gift(gift_code, user_id)

        logger.info(
            "gift_redeemed",
            gift_code=gift_code,
            redeemed_by=str(user_id),
        )

        return redeemed

    async def get_gift_info(self, gift_code: str) -> GiftPurchase:
        gift = await self._gift_repo.get_gift_by_code(gift_code)
        if not gift:
            raise NotFoundError("Gift not found")
        return gift
