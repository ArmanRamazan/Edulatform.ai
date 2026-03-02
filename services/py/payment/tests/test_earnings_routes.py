import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, ForbiddenError
from common.security import create_access_token
from app.domain.payment import (
    TeacherEarning,
    EarningStatus,
    EarningResponse,
    EarningsSummary,
    Payout,
    PayoutStatus,
)
from app.routes.earnings import router
from app.services.earnings_service import EarningsService


@pytest.fixture
def mock_earnings_service():
    return AsyncMock(spec=EarningsService)


@pytest.fixture
def test_app(mock_earnings_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._earnings_service = mock_earnings_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def teacher_id():
    return uuid4()


@pytest.fixture
def teacher_token(teacher_id):
    return create_access_token(
        str(teacher_id), "test-secret",
        extra_claims={"role": "teacher", "is_verified": True},
    )


@pytest.fixture
def student_token():
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def sample_earning(teacher_id):
    return TeacherEarning(
        id=uuid4(),
        teacher_id=teacher_id,
        course_id=uuid4(),
        payment_id=uuid4(),
        gross_amount=Decimal("49.99"),
        commission_rate=Decimal("0.30"),
        net_amount=Decimal("34.99"),
        status=EarningStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_summary(sample_earning):
    return EarningsSummary(
        total_gross=Decimal("49.99"),
        total_net=Decimal("34.99"),
        total_pending=Decimal("34.99"),
        total_paid=Decimal("0"),
        earnings=[EarningResponse(
            id=sample_earning.id,
            teacher_id=sample_earning.teacher_id,
            course_id=sample_earning.course_id,
            payment_id=sample_earning.payment_id,
            gross_amount=sample_earning.gross_amount,
            commission_rate=sample_earning.commission_rate,
            net_amount=sample_earning.net_amount,
            status=sample_earning.status,
            created_at=sample_earning.created_at,
        )],
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
async def test_get_summary_teacher_success(
    client, mock_earnings_service, sample_summary, teacher_token,
):
    mock_earnings_service.get_summary.return_value = sample_summary

    resp = await client.get(
        "/earnings/me/summary",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_gross"] == "49.99"
    assert len(body["earnings"]) == 1


@pytest.mark.asyncio
async def test_get_summary_student_forbidden(
    client, mock_earnings_service, teacher_token,
):
    mock_earnings_service.get_summary.side_effect = ForbiddenError(
        "Only teachers can view earnings"
    )

    resp = await client.get(
        "/earnings/me/summary",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_summary_no_auth(client):
    resp = await client.get("/earnings/me/summary")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_request_payout_success(
    client, mock_earnings_service, sample_payout, teacher_token,
):
    mock_earnings_service.request_payout.return_value = sample_payout

    resp = await client.post(
        "/earnings/payouts",
        json={"amount": "100.00"},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_list_payouts_success(
    client, mock_earnings_service, sample_payout, teacher_token,
):
    mock_earnings_service.list_payouts.return_value = ([sample_payout], 1)

    resp = await client.get(
        "/earnings/payouts",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
