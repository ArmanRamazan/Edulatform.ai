import pytest
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime, timezone

from common.errors import ForbiddenError
from app.domain.payment import (
    TeacherEarning,
    EarningStatus,
    Payout,
    PayoutStatus,
)
from app.repositories.earnings_repo import EarningsRepository
from app.services.earnings_service import EarningsService


@pytest.fixture
def teacher_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def payment_id():
    return uuid4()


@pytest.fixture
def mock_earnings_repo():
    return AsyncMock(spec=EarningsRepository)


@pytest.fixture
def earnings_service(mock_earnings_repo):
    return EarningsService(mock_earnings_repo)


@pytest.fixture
def sample_earning(teacher_id, course_id, payment_id):
    return TeacherEarning(
        id=uuid4(),
        teacher_id=teacher_id,
        course_id=course_id,
        payment_id=payment_id,
        gross_amount=Decimal("49.99"),
        commission_rate=Decimal("0.30"),
        net_amount=Decimal("34.99"),
        status=EarningStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_payout(teacher_id):
    return Payout(
        id=uuid4(),
        teacher_id=teacher_id,
        amount=Decimal("100.00"),
        stripe_transfer_id=None,
        status=PayoutStatus.PENDING,
        requested_at=datetime.now(timezone.utc),
        completed_at=None,
    )


@pytest.mark.asyncio
async def test_get_summary_success(
    earnings_service: EarningsService,
    mock_earnings_repo: AsyncMock,
    sample_earning: TeacherEarning,
    teacher_id,
):
    mock_earnings_repo.get_earnings_by_teacher.return_value = [sample_earning]

    result = await earnings_service.get_summary(teacher_id, role="teacher")

    assert result.total_gross == Decimal("49.99")
    assert result.total_net == Decimal("34.99")
    assert result.total_pending == Decimal("34.99")
    assert result.total_paid == Decimal("0")
    assert len(result.earnings) == 1


@pytest.mark.asyncio
async def test_get_summary_student_forbidden(
    earnings_service: EarningsService,
    teacher_id,
):
    with pytest.raises(ForbiddenError, match="Only teachers"):
        await earnings_service.get_summary(teacher_id, role="student")


@pytest.mark.asyncio
async def test_list_earnings_success(
    earnings_service: EarningsService,
    mock_earnings_repo: AsyncMock,
    sample_earning: TeacherEarning,
    teacher_id,
):
    mock_earnings_repo.list_earnings.return_value = ([sample_earning], 1)

    items, total = await earnings_service.list_earnings(teacher_id, role="teacher")

    assert len(items) == 1
    assert total == 1


@pytest.mark.asyncio
async def test_list_earnings_student_forbidden(
    earnings_service: EarningsService,
    teacher_id,
):
    with pytest.raises(ForbiddenError, match="Only teachers"):
        await earnings_service.list_earnings(teacher_id, role="student")


@pytest.mark.asyncio
async def test_request_payout_success(
    earnings_service: EarningsService,
    mock_earnings_repo: AsyncMock,
    sample_payout: Payout,
    teacher_id,
):
    mock_earnings_repo.create_payout.return_value = sample_payout

    result = await earnings_service.request_payout(
        teacher_id, role="teacher", amount=Decimal("100.00")
    )

    assert result.amount == Decimal("100.00")
    assert result.status == PayoutStatus.PENDING


@pytest.mark.asyncio
async def test_request_payout_student_forbidden(
    earnings_service: EarningsService,
    teacher_id,
):
    with pytest.raises(ForbiddenError, match="Only teachers"):
        await earnings_service.request_payout(
            teacher_id, role="student", amount=Decimal("100.00")
        )


@pytest.mark.asyncio
async def test_list_payouts_success(
    earnings_service: EarningsService,
    mock_earnings_repo: AsyncMock,
    sample_payout: Payout,
    teacher_id,
):
    mock_earnings_repo.list_payouts.return_value = ([sample_payout], 1)

    items, total = await earnings_service.list_payouts(teacher_id, role="teacher")

    assert len(items) == 1
    assert total == 1


@pytest.mark.asyncio
async def test_list_payouts_student_forbidden(
    earnings_service: EarningsService,
    teacher_id,
):
    with pytest.raises(ForbiddenError, match="Only teachers"):
        await earnings_service.list_payouts(teacher_id, role="student")
