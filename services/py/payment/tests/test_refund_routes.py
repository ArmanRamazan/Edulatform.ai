import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import (
    register_error_handlers, AppError, ConflictError,
    ForbiddenError, NotFoundError,
)
from common.security import create_access_token
from app.domain.refund import Refund, RefundStatus
from app.routes.refunds import router
from app.services.refund_service import RefundService


@pytest.fixture
def mock_refund_service():
    return AsyncMock(spec=RefundService)


@pytest.fixture
def test_app(mock_refund_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._refund_service = mock_refund_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def admin_id():
    return uuid4()


@pytest.fixture
def student_token(user_id):
    return create_access_token(
        str(user_id), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def admin_token(admin_id):
    return create_access_token(
        str(admin_id), "test-secret",
        extra_claims={"role": "admin", "is_verified": True},
    )


@pytest.fixture
def payment_id():
    return uuid4()


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


# --- POST /refunds ---


@pytest.mark.asyncio
async def test_request_refund_success(
    client, mock_refund_service, sample_refund, student_token, payment_id,
):
    mock_refund_service.request_refund.return_value = sample_refund

    resp = await client.post("/refunds", json={
        "payment_id": str(payment_id),
        "reason": "Changed my mind",
    }, headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 201
    assert resp.json()["status"] == "requested"


@pytest.mark.asyncio
async def test_request_refund_not_owner(
    client, mock_refund_service, student_token, payment_id,
):
    mock_refund_service.request_refund.side_effect = ForbiddenError(
        "You can only request refunds for your own payments"
    )

    resp = await client.post("/refunds", json={
        "payment_id": str(payment_id),
        "reason": "Reason",
    }, headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_request_refund_already_exists(
    client, mock_refund_service, student_token, payment_id,
):
    mock_refund_service.request_refund.side_effect = ConflictError(
        "A refund has already been requested for this payment"
    )

    resp = await client.post("/refunds", json={
        "payment_id": str(payment_id),
        "reason": "Reason",
    }, headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_request_refund_too_late(
    client, mock_refund_service, student_token, payment_id,
):
    mock_refund_service.request_refund.side_effect = AppError(
        "Refunds can only be requested within 14-day window", status_code=400,
    )

    resp = await client.post("/refunds", json={
        "payment_id": str(payment_id),
        "reason": "Reason",
    }, headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_request_refund_not_completed(
    client, mock_refund_service, student_token, payment_id,
):
    mock_refund_service.request_refund.side_effect = AppError(
        "Refunds can only be requested for completed payments", status_code=400,
    )

    resp = await client.post("/refunds", json={
        "payment_id": str(payment_id),
        "reason": "Reason",
    }, headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_request_refund_unauthenticated(client, payment_id):
    resp = await client.post("/refunds", json={
        "payment_id": str(payment_id),
        "reason": "Reason",
    })

    assert resp.status_code == 422


# --- GET /refunds/me ---


@pytest.mark.asyncio
async def test_get_my_refunds(
    client, mock_refund_service, sample_refund, student_token,
):
    mock_refund_service.get_my_refunds.return_value = ([sample_refund], 1)

    resp = await client.get("/refunds/me",
        headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


# --- GET /refunds (admin) ---


@pytest.mark.asyncio
async def test_list_refunds_admin(
    client, mock_refund_service, sample_refund, admin_token,
):
    mock_refund_service.list_refunds.return_value = ([sample_refund], 1)

    resp = await client.get("/refunds?status=requested",
        headers={"Authorization": f"Bearer {admin_token}"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_list_refunds_non_admin(
    client, mock_refund_service, student_token,
):
    mock_refund_service.list_refunds.side_effect = ForbiddenError(
        "Only admins can list all refunds"
    )

    resp = await client.get("/refunds",
        headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 403


# --- PATCH /refunds/{id}/approve ---


@pytest.mark.asyncio
async def test_approve_refund_success(
    client, mock_refund_service, sample_refund, admin_token,
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
    mock_refund_service.approve_refund.return_value = approved

    resp = await client.patch(f"/refunds/{sample_refund.id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_approve_already_processed(
    client, mock_refund_service, admin_token,
):
    mock_refund_service.approve_refund.side_effect = AppError(
        "Refund has already been processed", status_code=400,
    )

    resp = await client.patch(f"/refunds/{uuid4()}/approve",
        headers={"Authorization": f"Bearer {admin_token}"})

    assert resp.status_code == 400


# --- PATCH /refunds/{id}/reject ---


@pytest.mark.asyncio
async def test_reject_refund_success(
    client, mock_refund_service, sample_refund, admin_token,
):
    rejected = Refund(
        id=sample_refund.id,
        payment_id=sample_refund.payment_id,
        user_id=sample_refund.user_id,
        reason=sample_refund.reason,
        status=RefundStatus.REJECTED,
        amount=sample_refund.amount,
        admin_note="Course already completed",
        requested_at=sample_refund.requested_at,
        processed_at=datetime.now(timezone.utc),
    )
    mock_refund_service.reject_refund.return_value = rejected

    resp = await client.patch(f"/refunds/{sample_refund.id}/reject",
        json={"reason": "Course already completed"},
        headers={"Authorization": f"Bearer {admin_token}"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["admin_note"] == "Course already completed"
