import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import re
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from common.errors import register_error_handlers, ForbiddenError, NotFoundError
from common.security import create_access_token
from app.domain.invoice import InvoiceData, generate_invoice_number
from app.adapters.invoice import InvoicePDFGenerator
from app.services.invoice_service import InvoiceService


# ---------------------------------------------------------------------------
# Domain tests
# ---------------------------------------------------------------------------


def test_invoice_number_format():
    number = generate_invoice_number()
    assert re.match(r"^INV-\d{4}-\d{6}$", number)
    year = str(datetime.now(timezone.utc).year)
    assert number[4:8] == year


def test_invoice_data_immutable():
    data = InvoiceData(
        invoice_number="INV-2026-000001",
        payment_date=datetime.now(timezone.utc),
        buyer_name="Test User",
        buyer_email="test@example.com",
        course_title="Python 101",
        original_price=Decimal("49.99"),
        discount_amount=Decimal("0"),
        final_price=Decimal("49.99"),
        coupon_code=None,
    )
    assert data.invoice_number == "INV-2026-000001"
    assert data.coupon_code is None


# ---------------------------------------------------------------------------
# Adapter tests
# ---------------------------------------------------------------------------


def test_generate_invoice_pdf():
    data = InvoiceData(
        invoice_number="INV-2026-123456",
        payment_date=datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc),
        buyer_name="Иван Иванов",
        buyer_email="ivan@example.com",
        course_title="Python для начинающих",
        original_price=Decimal("99.99"),
        discount_amount=Decimal("0"),
        final_price=Decimal("99.99"),
        coupon_code=None,
    )
    generator = InvoicePDFGenerator()
    pdf_bytes = generator.generate_invoice(data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 100


def test_generate_invoice_pdf_with_discount():
    data = InvoiceData(
        invoice_number="INV-2026-654321",
        payment_date=datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc),
        buyer_name="Jane Doe",
        buyer_email="jane@example.com",
        course_title="Advanced ML",
        original_price=Decimal("199.99"),
        discount_amount=Decimal("50.00"),
        final_price=Decimal("149.99"),
        coupon_code="SAVE50",
    )
    generator = InvoicePDFGenerator()
    pdf_bytes = generator.generate_invoice(data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.fixture
def payment_id():
    return uuid4()


@pytest.fixture
def student_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def mock_payment_repo():
    return AsyncMock()


@pytest.fixture
def mock_pdf_generator():
    gen = MagicMock(spec=InvoicePDFGenerator)
    gen.generate_invoice.return_value = b"%PDF-fake"
    return gen


@pytest.fixture
def invoice_service(mock_payment_repo, mock_pdf_generator):
    return InvoiceService(
        payment_repo=mock_payment_repo,
        pdf_generator=mock_pdf_generator,
    )


@pytest.fixture
def sample_payment(payment_id, student_id, course_id):
    from app.domain.payment import Payment, PaymentStatus

    return Payment(
        id=payment_id,
        student_id=student_id,
        course_id=course_id,
        amount=Decimal("49.99"),
        status=PaymentStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
    )


async def test_generate_invoice_success(
    invoice_service, mock_payment_repo, mock_pdf_generator,
    sample_payment, student_id, payment_id,
):
    mock_payment_repo.get_by_id.return_value = sample_payment

    pdf_bytes, filename = await invoice_service.generate_invoice(
        user_id=student_id,
        payment_id=payment_id,
        role="student",
        buyer_name="Test User",
        buyer_email="test@example.com",
        course_title="Python 101",
    )

    assert pdf_bytes == b"%PDF-fake"
    assert filename == f"invoice_{payment_id}.pdf"
    mock_pdf_generator.generate_invoice.assert_called_once()


async def test_generate_invoice_payment_not_found(
    invoice_service, mock_payment_repo,
):
    mock_payment_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Payment not found"):
        await invoice_service.generate_invoice(
            user_id=uuid4(),
            payment_id=uuid4(),
            role="student",
            buyer_name="Test",
            buyer_email="t@t.com",
            course_title="Test",
        )


async def test_generate_invoice_not_owner(
    invoice_service, mock_payment_repo, sample_payment, payment_id,
):
    mock_payment_repo.get_by_id.return_value = sample_payment
    other_user = uuid4()

    with pytest.raises(ForbiddenError):
        await invoice_service.generate_invoice(
            user_id=other_user,
            payment_id=payment_id,
            role="student",
            buyer_name="Other",
            buyer_email="other@t.com",
            course_title="Test",
        )


async def test_generate_invoice_admin_access(
    invoice_service, mock_payment_repo, mock_pdf_generator,
    sample_payment, payment_id,
):
    mock_payment_repo.get_by_id.return_value = sample_payment
    admin_id = uuid4()

    pdf_bytes, filename = await invoice_service.generate_invoice(
        user_id=admin_id,
        payment_id=payment_id,
        role="admin",
        buyer_name="Admin",
        buyer_email="admin@t.com",
        course_title="Test",
    )

    assert pdf_bytes == b"%PDF-fake"


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_invoice_service():
    return AsyncMock(spec=InvoiceService)


@pytest.fixture
def test_app(mock_invoice_service):
    from app.routes.invoices import router

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._invoice_service = mock_invoice_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def student_token(student_id):
    return create_access_token(
        str(student_id), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def admin_token():
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={"role": "admin", "is_verified": True},
    )


async def test_get_invoice_success(
    client, mock_invoice_service, student_token, payment_id,
):
    mock_invoice_service.generate_invoice.return_value = (
        b"%PDF-test-content",
        f"invoice_{payment_id}.pdf",
    )

    resp = await client.get(
        f"/payments/{payment_id}/invoice",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert f"invoice_{payment_id}.pdf" in resp.headers["content-disposition"]
    assert resp.content == b"%PDF-test-content"


async def test_get_invoice_not_owner(
    client, mock_invoice_service, student_token, payment_id,
):
    mock_invoice_service.generate_invoice.side_effect = ForbiddenError(
        "Access denied"
    )

    resp = await client.get(
        f"/payments/{payment_id}/invoice",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 403


async def test_get_invoice_admin_access(
    client, mock_invoice_service, admin_token, payment_id,
):
    mock_invoice_service.generate_invoice.return_value = (
        b"%PDF-admin-content",
        f"invoice_{payment_id}.pdf",
    )

    resp = await client.get(
        f"/payments/{payment_id}/invoice",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    assert resp.content == b"%PDF-admin-content"


async def test_get_invoice_payment_not_found(
    client, mock_invoice_service, student_token,
):
    mock_invoice_service.generate_invoice.side_effect = NotFoundError(
        "Payment not found"
    )

    resp = await client.get(
        f"/payments/{uuid4()}/invoice",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 404


async def test_get_invoice_unauthenticated(client, payment_id):
    resp = await client.get(f"/payments/{payment_id}/invoice")

    assert resp.status_code == 422
