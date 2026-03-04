from __future__ import annotations

import re
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from common.errors import AppError, NotFoundError
from app.domain.payment import Payment, PaymentStatus
from app.domain.gift import GiftPurchase, GiftStatus
from app.repositories.gift_repo import GiftRepository
from app.repositories.payment_repo import PaymentRepository
from app.services.gift_service import GiftService

GIFT_CODE_PATTERN = re.compile(r"^GIFT-[A-Z0-9]{4}-[A-Z0-9]{4}$")


@pytest.fixture
def mock_gift_repo():
    return AsyncMock(spec=GiftRepository)


@pytest.fixture
def mock_payment_repo():
    return AsyncMock(spec=PaymentRepository)


@pytest.fixture
def gift_service(mock_gift_repo, mock_payment_repo):
    return GiftService(
        gift_repo=mock_gift_repo,
        payment_repo=mock_payment_repo,
    )


@pytest.fixture
def buyer_id():
    return uuid4()


@pytest.fixture
def recipient_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def payment_id():
    return uuid4()


@pytest.fixture
def sample_gift(buyer_id, course_id, payment_id):
    return GiftPurchase(
        id=uuid4(),
        buyer_id=buyer_id,
        recipient_email="friend@example.com",
        course_id=course_id,
        payment_id=payment_id,
        gift_code="GIFT-AB12-CD34",
        status=GiftStatus.PURCHASED,
        message="Happy birthday!",
        created_at=datetime.now(timezone.utc),
        redeemed_at=None,
        redeemed_by=None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
    )


@pytest.fixture
def sample_payment(payment_id, buyer_id, course_id):
    return Payment(
        id=payment_id,
        student_id=buyer_id,
        course_id=course_id,
        amount=Decimal("49.99"),
        status=PaymentStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )


# --- purchase_gift ---


@pytest.mark.asyncio
async def test_purchase_gift_success(
    gift_service, mock_gift_repo, mock_payment_repo,
    sample_gift, sample_payment, buyer_id, course_id,
):
    mock_payment_repo.create.return_value = sample_payment
    mock_gift_repo.create_gift.return_value = sample_gift

    result = await gift_service.purchase_gift(
        buyer_id=buyer_id,
        course_id=course_id,
        recipient_email="friend@example.com",
        message="Happy birthday!",
    )

    assert result.status == GiftStatus.PURCHASED
    assert result.recipient_email == "friend@example.com"
    assert result.message == "Happy birthday!"
    mock_payment_repo.create.assert_called_once()
    mock_gift_repo.create_gift.assert_called_once()


@pytest.mark.asyncio
async def test_purchase_gift_invalid_email(gift_service, buyer_id, course_id):
    with pytest.raises(AppError, match="Invalid email"):
        await gift_service.purchase_gift(
            buyer_id=buyer_id,
            course_id=course_id,
            recipient_email="not-an-email",
        )


@pytest.mark.asyncio
async def test_purchase_gift_long_message(gift_service, buyer_id, course_id):
    with pytest.raises(AppError, match="500 characters"):
        await gift_service.purchase_gift(
            buyer_id=buyer_id,
            course_id=course_id,
            recipient_email="friend@example.com",
            message="x" * 501,
        )


@pytest.mark.asyncio
async def test_gift_code_format(
    gift_service, mock_gift_repo, mock_payment_repo,
    sample_gift, sample_payment, buyer_id, course_id,
):
    mock_payment_repo.create.return_value = sample_payment
    mock_gift_repo.create_gift.return_value = sample_gift

    await gift_service.purchase_gift(
        buyer_id=buyer_id,
        course_id=course_id,
        recipient_email="friend@example.com",
    )

    call_kwargs = mock_gift_repo.create_gift.call_args
    gift_code = call_kwargs.kwargs.get("gift_code") or call_kwargs[1].get("gift_code")
    assert GIFT_CODE_PATTERN.match(gift_code)


@pytest.mark.asyncio
async def test_purchase_gift_expires_in_90_days(
    gift_service, mock_gift_repo, mock_payment_repo,
    sample_gift, sample_payment, buyer_id, course_id,
):
    mock_payment_repo.create.return_value = sample_payment
    mock_gift_repo.create_gift.return_value = sample_gift

    await gift_service.purchase_gift(
        buyer_id=buyer_id,
        course_id=course_id,
        recipient_email="friend@example.com",
    )

    call_kwargs = mock_gift_repo.create_gift.call_args
    expires_at = call_kwargs.kwargs.get("expires_at") or call_kwargs[1].get("expires_at")
    now = datetime.now(timezone.utc)
    delta = expires_at - now
    assert 89 <= delta.days <= 90


# --- get_my_sent_gifts ---


@pytest.mark.asyncio
async def test_get_sent_gifts(
    gift_service, mock_gift_repo, sample_gift, buyer_id,
):
    mock_gift_repo.get_sent_gifts.return_value = ([sample_gift], 1)

    items, total = await gift_service.get_my_sent_gifts(buyer_id)

    assert len(items) == 1
    assert total == 1
    mock_gift_repo.get_sent_gifts.assert_called_once_with(buyer_id, 20, 0)


# --- redeem_gift ---


@pytest.mark.asyncio
async def test_redeem_gift_success(
    gift_service, mock_gift_repo, sample_gift, recipient_id,
):
    mock_gift_repo.get_gift_by_code.return_value = sample_gift
    redeemed = GiftPurchase(
        id=sample_gift.id,
        buyer_id=sample_gift.buyer_id,
        recipient_email=sample_gift.recipient_email,
        course_id=sample_gift.course_id,
        payment_id=sample_gift.payment_id,
        gift_code=sample_gift.gift_code,
        status=GiftStatus.REDEEMED,
        message=sample_gift.message,
        created_at=sample_gift.created_at,
        redeemed_at=datetime.now(timezone.utc),
        redeemed_by=recipient_id,
        expires_at=sample_gift.expires_at,
    )
    mock_gift_repo.redeem_gift.return_value = redeemed

    result = await gift_service.redeem_gift(
        user_id=recipient_id,
        gift_code="GIFT-AB12-CD34",
    )

    assert result.status == GiftStatus.REDEEMED
    assert result.redeemed_by == recipient_id


@pytest.mark.asyncio
async def test_redeem_gift_not_found(gift_service, mock_gift_repo, recipient_id):
    mock_gift_repo.get_gift_by_code.return_value = None

    with pytest.raises(NotFoundError, match="Gift not found"):
        await gift_service.redeem_gift(
            user_id=recipient_id,
            gift_code="GIFT-XXXX-YYYY",
        )


@pytest.mark.asyncio
async def test_redeem_gift_already_redeemed(
    gift_service, mock_gift_repo, sample_gift, recipient_id,
):
    redeemed_gift = GiftPurchase(
        id=sample_gift.id,
        buyer_id=sample_gift.buyer_id,
        recipient_email=sample_gift.recipient_email,
        course_id=sample_gift.course_id,
        payment_id=sample_gift.payment_id,
        gift_code=sample_gift.gift_code,
        status=GiftStatus.REDEEMED,
        message=sample_gift.message,
        created_at=sample_gift.created_at,
        redeemed_at=datetime.now(timezone.utc),
        redeemed_by=uuid4(),
        expires_at=sample_gift.expires_at,
    )
    mock_gift_repo.get_gift_by_code.return_value = redeemed_gift

    with pytest.raises(AppError, match="already been redeemed"):
        await gift_service.redeem_gift(
            user_id=recipient_id,
            gift_code="GIFT-AB12-CD34",
        )


@pytest.mark.asyncio
async def test_redeem_gift_expired(
    gift_service, mock_gift_repo, sample_gift, recipient_id,
):
    expired_gift = GiftPurchase(
        id=sample_gift.id,
        buyer_id=sample_gift.buyer_id,
        recipient_email=sample_gift.recipient_email,
        course_id=sample_gift.course_id,
        payment_id=sample_gift.payment_id,
        gift_code=sample_gift.gift_code,
        status=GiftStatus.PURCHASED,
        message=sample_gift.message,
        created_at=sample_gift.created_at,
        redeemed_at=None,
        redeemed_by=None,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    mock_gift_repo.get_gift_by_code.return_value = expired_gift

    with pytest.raises(AppError, match="expired"):
        await gift_service.redeem_gift(
            user_id=recipient_id,
            gift_code="GIFT-AB12-CD34",
        )


# --- get_gift_info ---


@pytest.mark.asyncio
async def test_get_gift_info(gift_service, mock_gift_repo, sample_gift):
    mock_gift_repo.get_gift_by_code.return_value = sample_gift

    result = await gift_service.get_gift_info("GIFT-AB12-CD34")

    assert result.gift_code == "GIFT-AB12-CD34"
    assert result.course_id == sample_gift.course_id


@pytest.mark.asyncio
async def test_get_gift_info_not_found(gift_service, mock_gift_repo):
    mock_gift_repo.get_gift_by_code.return_value = None

    with pytest.raises(NotFoundError, match="Gift not found"):
        await gift_service.get_gift_info("GIFT-XXXX-YYYY")
