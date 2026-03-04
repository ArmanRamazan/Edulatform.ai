import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from common.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.domain.payment import Payment, PaymentStatus
from app.domain.refund import Refund, RefundStatus
from app.repositories.payment_repo import PaymentRepository
from app.repositories.refund_repo import RefundRepository
from app.services.refund_service import RefundService


@pytest.fixture
def mock_refund_repo():
    return AsyncMock(spec=RefundRepository)


@pytest.fixture
def mock_payment_repo():
    return AsyncMock(spec=PaymentRepository)


@pytest.fixture
def refund_service(mock_refund_repo, mock_payment_repo):
    return RefundService(
        refund_repo=mock_refund_repo,
        payment_repo=mock_payment_repo,
    )


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def admin_id():
    return uuid4()


@pytest.fixture
def payment_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def completed_payment(payment_id, user_id, course_id):
    return Payment(
        id=payment_id,
        student_id=user_id,
        course_id=course_id,
        amount=Decimal("49.99"),
        status=PaymentStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_refund(payment_id, user_id):
    return Refund(
        id=uuid4(),
        payment_id=payment_id,
        user_id=user_id,
        reason="Changed my mind",
        status=RefundStatus.REQUESTED,
        amount=Decimal("49.99"),
        admin_note=None,
        requested_at=datetime.now(timezone.utc),
        processed_at=None,
    )


# --- request_refund ---


@pytest.mark.asyncio
async def test_request_refund_success(
    refund_service, mock_refund_repo, mock_payment_repo,
    completed_payment, sample_refund, user_id, payment_id,
):
    mock_payment_repo.get_by_id.return_value = completed_payment
    mock_refund_repo.get_by_payment_id.return_value = None
    mock_refund_repo.create_refund.return_value = sample_refund

    result = await refund_service.request_refund(
        user_id=user_id,
        payment_id=payment_id,
        reason="Changed my mind",
    )

    assert result.status == RefundStatus.REQUESTED
    assert result.amount == Decimal("49.99")
    mock_refund_repo.create_refund.assert_called_once_with(
        payment_id=payment_id,
        user_id=user_id,
        reason="Changed my mind",
        amount=completed_payment.amount,
    )


@pytest.mark.asyncio
async def test_request_refund_payment_not_found(
    refund_service, mock_payment_repo, user_id,
):
    mock_payment_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Payment not found"):
        await refund_service.request_refund(
            user_id=user_id,
            payment_id=uuid4(),
            reason="Reason",
        )


@pytest.mark.asyncio
async def test_request_refund_not_owner(
    refund_service, mock_payment_repo, completed_payment, payment_id,
):
    mock_payment_repo.get_by_id.return_value = completed_payment
    other_user = uuid4()

    with pytest.raises(ForbiddenError, match="own payments"):
        await refund_service.request_refund(
            user_id=other_user,
            payment_id=payment_id,
            reason="Reason",
        )


@pytest.mark.asyncio
async def test_request_refund_not_completed(
    refund_service, mock_payment_repo, user_id, payment_id, course_id,
):
    pending_payment = Payment(
        id=payment_id,
        student_id=user_id,
        course_id=course_id,
        amount=Decimal("49.99"),
        status=PaymentStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    mock_payment_repo.get_by_id.return_value = pending_payment

    with pytest.raises(AppError, match="completed payments"):
        await refund_service.request_refund(
            user_id=user_id,
            payment_id=payment_id,
            reason="Reason",
        )


@pytest.mark.asyncio
async def test_request_refund_already_exists(
    refund_service, mock_payment_repo, mock_refund_repo,
    completed_payment, sample_refund, user_id, payment_id,
):
    mock_payment_repo.get_by_id.return_value = completed_payment
    mock_refund_repo.get_by_payment_id.return_value = sample_refund

    with pytest.raises(ConflictError, match="already been requested"):
        await refund_service.request_refund(
            user_id=user_id,
            payment_id=payment_id,
            reason="Reason",
        )


@pytest.mark.asyncio
async def test_request_refund_too_late(
    refund_service, mock_payment_repo, mock_refund_repo,
    user_id, payment_id, course_id,
):
    old_payment = Payment(
        id=payment_id,
        student_id=user_id,
        course_id=course_id,
        amount=Decimal("49.99"),
        status=PaymentStatus.COMPLETED,
        created_at=datetime.now(timezone.utc) - timedelta(days=15),
    )
    mock_payment_repo.get_by_id.return_value = old_payment
    mock_refund_repo.get_by_payment_id.return_value = None

    with pytest.raises(AppError, match="14-day"):
        await refund_service.request_refund(
            user_id=user_id,
            payment_id=payment_id,
            reason="Reason",
        )


# --- get_my_refunds ---


@pytest.mark.asyncio
async def test_get_my_refunds(
    refund_service, mock_refund_repo, sample_refund, user_id,
):
    mock_refund_repo.get_user_refunds.return_value = ([sample_refund], 1)

    items, total = await refund_service.get_my_refunds(user_id)

    assert len(items) == 1
    assert total == 1
    mock_refund_repo.get_user_refunds.assert_called_once_with(user_id, 20, 0)


# --- list_refunds (admin) ---


@pytest.mark.asyncio
async def test_list_refunds_admin(
    refund_service, mock_refund_repo, sample_refund, admin_id,
):
    mock_refund_repo.list_all_refunds.return_value = ([sample_refund], 1)

    items, total = await refund_service.list_refunds(
        role="admin", status_filter="requested",
    )

    assert len(items) == 1
    assert total == 1
    mock_refund_repo.list_all_refunds.assert_called_once_with("requested", 20, 0)


@pytest.mark.asyncio
async def test_list_refunds_non_admin(refund_service):
    with pytest.raises(ForbiddenError, match="admin"):
        await refund_service.list_refunds(role="student")


# --- approve_refund ---


@pytest.mark.asyncio
async def test_approve_refund_success(
    refund_service, mock_refund_repo, mock_payment_repo,
    sample_refund, admin_id,
):
    approved = Refund(
        id=sample_refund.id,
        payment_id=sample_refund.payment_id,
        user_id=sample_refund.user_id,
        reason=sample_refund.reason,
        status=RefundStatus.APPROVED,
        amount=sample_refund.amount,
        admin_note=None,
        requested_at=sample_refund.requested_at,
        processed_at=datetime.now(timezone.utc),
    )
    mock_refund_repo.get_refund.return_value = sample_refund
    mock_refund_repo.update_status.return_value = approved

    result = await refund_service.approve_refund(
        admin_id=admin_id,
        refund_id=sample_refund.id,
        role="admin",
    )

    assert result.status == RefundStatus.APPROVED
    mock_payment_repo.update_status.assert_called_once_with(
        sample_refund.payment_id, PaymentStatus.REFUNDED,
    )


@pytest.mark.asyncio
async def test_approve_refund_non_admin(refund_service):
    with pytest.raises(ForbiddenError, match="admin"):
        await refund_service.approve_refund(
            admin_id=uuid4(),
            refund_id=uuid4(),
            role="student",
        )


@pytest.mark.asyncio
async def test_approve_already_processed(
    refund_service, mock_refund_repo, admin_id,
):
    processed_refund = Refund(
        id=uuid4(),
        payment_id=uuid4(),
        user_id=uuid4(),
        reason="Reason",
        status=RefundStatus.APPROVED,
        amount=Decimal("49.99"),
        admin_note=None,
        requested_at=datetime.now(timezone.utc),
        processed_at=datetime.now(timezone.utc),
    )
    mock_refund_repo.get_refund.return_value = processed_refund

    with pytest.raises(AppError, match="already been processed"):
        await refund_service.approve_refund(
            admin_id=admin_id,
            refund_id=processed_refund.id,
            role="admin",
        )


# --- reject_refund ---


@pytest.mark.asyncio
async def test_reject_refund_success(
    refund_service, mock_refund_repo, sample_refund, admin_id,
):
    rejected = Refund(
        id=sample_refund.id,
        payment_id=sample_refund.payment_id,
        user_id=sample_refund.user_id,
        reason=sample_refund.reason,
        status=RefundStatus.REJECTED,
        amount=sample_refund.amount,
        admin_note="Course was completed",
        requested_at=sample_refund.requested_at,
        processed_at=datetime.now(timezone.utc),
    )
    mock_refund_repo.get_refund.return_value = sample_refund
    mock_refund_repo.update_status.return_value = rejected

    result = await refund_service.reject_refund(
        admin_id=admin_id,
        refund_id=sample_refund.id,
        role="admin",
        reason="Course was completed",
    )

    assert result.status == RefundStatus.REJECTED
    assert result.admin_note == "Course was completed"


@pytest.mark.asyncio
async def test_reject_refund_non_admin(refund_service):
    with pytest.raises(ForbiddenError, match="admin"):
        await refund_service.reject_refund(
            admin_id=uuid4(),
            refund_id=uuid4(),
            role="student",
            reason="No",
        )
