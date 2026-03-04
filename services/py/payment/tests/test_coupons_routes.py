import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, ForbiddenError, NotFoundError, AppError
from common.security import create_access_token
from app.domain.coupon import (
    Coupon, DiscountType, DiscountResult,
    CouponResponse, CouponListResponse, DiscountResultResponse,
)
from app.routes.coupons import router
from app.services.coupon_service import CouponService


@pytest.fixture
def mock_coupon_service():
    return AsyncMock(spec=CouponService)


@pytest.fixture
def test_app(mock_coupon_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._coupon_service = mock_coupon_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def admin_id():
    return uuid4()


@pytest.fixture
def student_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def admin_token(admin_id):
    return create_access_token(
        str(admin_id), "test-secret",
        extra_claims={"role": "admin", "is_verified": True},
    )


@pytest.fixture
def student_token(student_id):
    return create_access_token(
        str(student_id), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def sample_coupon(admin_id):
    return Coupon(
        id=uuid4(),
        code="SAVE20",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("20"),
        max_uses=100,
        current_uses=5,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        course_id=None,
        created_by=admin_id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


class TestCreateCouponRoute:
    async def test_create_coupon_admin(self, client, mock_coupon_service, admin_token, sample_coupon):
        mock_coupon_service.create_coupon.return_value = sample_coupon

        resp = await client.post("/coupons", json={
            "code": "SAVE20",
            "discount_type": "percentage",
            "discount_value": "20",
            "valid_from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }, headers={"Authorization": f"Bearer {admin_token}"})

        assert resp.status_code == 201
        assert resp.json()["code"] == "SAVE20"

    async def test_create_coupon_non_admin(self, client, mock_coupon_service, student_token):
        mock_coupon_service.create_coupon.side_effect = ForbiddenError("Admin only")

        resp = await client.post("/coupons", json={
            "code": "SAVE20",
            "discount_type": "percentage",
            "discount_value": "20",
            "valid_from": datetime.now(timezone.utc).isoformat(),
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }, headers={"Authorization": f"Bearer {student_token}"})

        assert resp.status_code == 403


class TestListCouponsRoute:
    async def test_list_coupons_admin(self, client, mock_coupon_service, admin_token, sample_coupon):
        mock_coupon_service.list_coupons.return_value = ([sample_coupon], 1)

        resp = await client.get("/coupons", headers={"Authorization": f"Bearer {admin_token}"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1

    async def test_list_coupons_non_admin(self, client, mock_coupon_service, student_token):
        mock_coupon_service.list_coupons.side_effect = ForbiddenError("Admin only")

        resp = await client.get("/coupons", headers={"Authorization": f"Bearer {student_token}"})

        assert resp.status_code == 403


class TestValidateCouponRoute:
    async def test_validate_coupon(self, client, mock_coupon_service, student_token, course_id):
        mock_coupon_service.validate_coupon.return_value = DiscountResult(
            original_price=Decimal("100"),
            discount_amount=Decimal("20"),
            final_price=Decimal("80"),
            coupon_code="SAVE20",
        )

        resp = await client.post("/coupons/validate", json={
            "code": "SAVE20",
            "course_id": str(course_id),
            "amount": "100",
        }, headers={"Authorization": f"Bearer {student_token}"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["final_price"] == "80.00" or float(body["final_price"]) == 80

    async def test_validate_coupon_not_found(self, client, mock_coupon_service, student_token, course_id):
        mock_coupon_service.validate_coupon.side_effect = NotFoundError("Coupon not found")

        resp = await client.post("/coupons/validate", json={
            "code": "INVALID",
            "course_id": str(course_id),
            "amount": "100",
        }, headers={"Authorization": f"Bearer {student_token}"})

        assert resp.status_code == 404

    async def test_validate_coupon_already_used(self, client, mock_coupon_service, student_token, course_id):
        mock_coupon_service.validate_coupon.side_effect = AppError(
            "Coupon already used", status_code=400
        )

        resp = await client.post("/coupons/validate", json={
            "code": "SAVE20",
            "course_id": str(course_id),
            "amount": "100",
        }, headers={"Authorization": f"Bearer {student_token}"})

        assert resp.status_code == 400


class TestDeactivateCouponRoute:
    async def test_deactivate_admin(self, client, mock_coupon_service, admin_token):
        coupon_id = uuid4()
        mock_coupon_service.deactivate_coupon.return_value = None

        resp = await client.patch(
            f"/coupons/{coupon_id}/deactivate",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert resp.status_code == 204

    async def test_deactivate_non_admin(self, client, mock_coupon_service, student_token):
        mock_coupon_service.deactivate_coupon.side_effect = ForbiddenError("Admin only")

        resp = await client.patch(
            f"/coupons/{uuid4()}/deactivate",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 403


class TestPaymentWithCoupon:
    async def test_payment_with_coupon(self, student_token, student_id, course_id):
        """Payment with coupon_code should apply discount."""
        from app.services.payment_service import PaymentService
        from app.services.coupon_service import CouponService
        from app.domain.payment import Payment, PaymentStatus
        from app.routes.payments import router as payments_router

        mock_payment_service = AsyncMock(spec=PaymentService)
        mock_coupon_svc = AsyncMock(spec=CouponService)

        payment = Payment(
            id=uuid4(),
            student_id=student_id,
            course_id=course_id,
            amount=Decimal("80.00"),
            status=PaymentStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
        )
        mock_payment_service.create.return_value = payment
        mock_coupon_svc.validate_coupon.return_value = DiscountResult(
            original_price=Decimal("100"),
            discount_amount=Decimal("20"),
            final_price=Decimal("80"),
            coupon_code="SAVE20",
        )

        app = FastAPI()
        register_error_handlers(app)
        app.include_router(payments_router)

        import app.main as main_module
        main_module.app_settings = type("S", (), {
            "jwt_secret": "test-secret",
            "jwt_algorithm": "HS256",
        })()
        main_module._payment_service = mock_payment_service
        main_module._coupon_service = mock_coupon_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/payments", json={
                "course_id": str(course_id),
                "amount": "100.00",
                "coupon_code": "SAVE20",
            }, headers={"Authorization": f"Bearer {student_token}"})

        assert resp.status_code == 201
        assert float(resp.json()["amount"]) == 80.0
        mock_coupon_svc.validate_coupon.assert_awaited_once()
        mock_coupon_svc.apply_coupon.assert_awaited_once()
