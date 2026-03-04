from __future__ import annotations

import re
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, AppError, NotFoundError
from common.security import create_access_token
from app.domain.gift import GiftPurchase, GiftStatus
from app.routes.gifts import router
from app.services.gift_service import GiftService


@pytest.fixture
def mock_gift_service():
    return AsyncMock(spec=GiftService)


@pytest.fixture
def test_app(mock_gift_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._gift_service = mock_gift_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def buyer_id():
    return uuid4()


@pytest.fixture
def recipient_id():
    return uuid4()


@pytest.fixture
def student_token(buyer_id):
    return create_access_token(
        str(buyer_id), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def recipient_token(recipient_id):
    return create_access_token(
        str(recipient_id), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


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


# --- POST /gifts ---


@pytest.mark.asyncio
async def test_purchase_gift_success(
    client, mock_gift_service, sample_gift, student_token, course_id,
):
    mock_gift_service.purchase_gift.return_value = sample_gift

    resp = await client.post("/gifts", json={
        "course_id": str(course_id),
        "recipient_email": "friend@example.com",
        "message": "Happy birthday!",
    }, headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "purchased"
    assert body["recipient_email"] == "friend@example.com"
    assert body["gift_code"] == "GIFT-AB12-CD34"


@pytest.mark.asyncio
async def test_purchase_gift_invalid_email(
    client, mock_gift_service, student_token, course_id,
):
    mock_gift_service.purchase_gift.side_effect = AppError(
        "Invalid email format", status_code=422,
    )

    resp = await client.post("/gifts", json={
        "course_id": str(course_id),
        "recipient_email": "not-an-email",
    }, headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_purchase_gift_long_message(
    client, mock_gift_service, student_token, course_id,
):
    mock_gift_service.purchase_gift.side_effect = AppError(
        "Message cannot exceed 500 characters", status_code=422,
    )

    resp = await client.post("/gifts", json={
        "course_id": str(course_id),
        "recipient_email": "friend@example.com",
        "message": "x" * 501,
    }, headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_purchase_gift_unauthenticated(client, course_id):
    resp = await client.post("/gifts", json={
        "course_id": str(course_id),
        "recipient_email": "friend@example.com",
    })

    assert resp.status_code == 422


# --- GET /gifts/me/sent ---


@pytest.mark.asyncio
async def test_get_sent_gifts(
    client, mock_gift_service, sample_gift, student_token,
):
    mock_gift_service.get_my_sent_gifts.return_value = ([sample_gift], 1)

    resp = await client.get("/gifts/me/sent",
        headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


# --- POST /gifts/redeem ---


@pytest.mark.asyncio
async def test_redeem_gift_success(
    client, mock_gift_service, sample_gift, recipient_token, recipient_id,
):
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
    mock_gift_service.redeem_gift.return_value = redeemed

    resp = await client.post("/gifts/redeem", json={
        "gift_code": "GIFT-AB12-CD34",
    }, headers={"Authorization": f"Bearer {recipient_token}"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "redeemed"


@pytest.mark.asyncio
async def test_redeem_gift_not_found(
    client, mock_gift_service, recipient_token,
):
    mock_gift_service.redeem_gift.side_effect = NotFoundError("Gift not found")

    resp = await client.post("/gifts/redeem", json={
        "gift_code": "GIFT-XXXX-YYYY",
    }, headers={"Authorization": f"Bearer {recipient_token}"})

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_redeem_gift_already_redeemed(
    client, mock_gift_service, recipient_token,
):
    mock_gift_service.redeem_gift.side_effect = AppError(
        "Gift has already been redeemed", status_code=400,
    )

    resp = await client.post("/gifts/redeem", json={
        "gift_code": "GIFT-AB12-CD34",
    }, headers={"Authorization": f"Bearer {recipient_token}"})

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_redeem_gift_expired(
    client, mock_gift_service, recipient_token,
):
    mock_gift_service.redeem_gift.side_effect = AppError(
        "Gift has expired", status_code=400,
    )

    resp = await client.post("/gifts/redeem", json={
        "gift_code": "GIFT-AB12-CD34",
    }, headers={"Authorization": f"Bearer {recipient_token}"})

    assert resp.status_code == 400


# --- GET /gifts/{gift_code}/info ---


@pytest.mark.asyncio
async def test_get_gift_info_public(
    client, mock_gift_service, sample_gift,
):
    mock_gift_service.get_gift_info.return_value = sample_gift

    resp = await client.get("/gifts/GIFT-AB12-CD34/info")

    assert resp.status_code == 200
    body = resp.json()
    assert body["gift_code"] == "GIFT-AB12-CD34"
    assert body["status"] == "purchased"
    assert body["course_id"] == str(sample_gift.course_id)
    # Public endpoint should not expose buyer_id
    assert "buyer_id" not in body


@pytest.mark.asyncio
async def test_get_gift_info_not_found(client, mock_gift_service):
    mock_gift_service.get_gift_info.side_effect = NotFoundError("Gift not found")

    resp = await client.get("/gifts/GIFT-XXXX-YYYY/info")

    assert resp.status_code == 404
