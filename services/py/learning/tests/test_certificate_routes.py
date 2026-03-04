from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, ConflictError, NotFoundError
from common.security import create_access_token
from app.domain.certificate import Certificate, CertificateListResponse, CertificateResponse
from app.routes.certificates import router
from app.routes.internal_certificates import router as internal_router
from app.services.certificate_service import CertificateService


@pytest.fixture
def mock_cert_service():
    return AsyncMock(spec=CertificateService)


@pytest.fixture
def test_app(mock_cert_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    app.include_router(internal_router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._certificate_service = mock_cert_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def student_token():
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def student_id(student_token):
    import jwt
    payload = jwt.decode(student_token, "test-secret", algorithms=["HS256"])
    return payload["sub"]


def _make_certificate(user_id, course_id) -> Certificate:
    return Certificate(
        id=uuid4(),
        user_id=user_id if isinstance(user_id, type(uuid4())) else uuid4(),
        course_id=course_id,
        issued_at=datetime.now(timezone.utc),
        certificate_number="CERT-2026-A1B2C3",
        template_data={},
    )


class TestIssueCertificate:
    async def test_issue_returns_201(
        self, client, mock_cert_service, student_token,
    ):
        course_id = uuid4()
        cert = _make_certificate(uuid4(), course_id)
        mock_cert_service.issue_certificate.return_value = cert

        resp = await client.post(
            "/certificates/issue",
            json={"course_id": str(course_id)},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["certificate_number"] == "CERT-2026-A1B2C3"
        assert body["course_id"] == str(course_id)

    async def test_issue_duplicate_returns_409(
        self, client, mock_cert_service, student_token,
    ):
        mock_cert_service.issue_certificate.side_effect = ConflictError(
            "Certificate already issued for this course"
        )

        resp = await client.post(
            "/certificates/issue",
            json={"course_id": str(uuid4())},
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 409

    async def test_issue_unauthenticated_returns_error(self, client):
        resp = await client.post(
            "/certificates/issue",
            json={"course_id": str(uuid4())},
        )
        assert resp.status_code in (401, 422)


class TestGetMyCertificates:
    async def test_get_my_certificates_returns_200(
        self, client, mock_cert_service, student_token,
    ):
        mock_cert_service.get_my_certificates.return_value = CertificateListResponse(
            certificates=[
                CertificateResponse(
                    id=uuid4(),
                    user_id=uuid4(),
                    course_id=uuid4(),
                    issued_at=datetime.now(timezone.utc),
                    certificate_number="CERT-2026-A1B2C3",
                ),
            ],
            total=1,
        )

        resp = await client.get(
            "/certificates/me",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert len(body["certificates"]) == 1

    async def test_get_my_certificates_unauthenticated(self, client):
        resp = await client.get("/certificates/me")
        assert resp.status_code in (401, 422)


class TestGetCertificate:
    async def test_get_certificate_returns_200(
        self, client, mock_cert_service, student_token,
    ):
        cert = _make_certificate(uuid4(), uuid4())
        mock_cert_service.get_certificate.return_value = cert

        resp = await client.get(
            f"/certificates/{cert.id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["certificate_number"] == cert.certificate_number

    async def test_get_certificate_not_found(
        self, client, mock_cert_service, student_token,
    ):
        mock_cert_service.get_certificate.side_effect = NotFoundError(
            "Certificate not found"
        )

        resp = await client.get(
            f"/certificates/{uuid4()}",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 404


class TestAutoIssueCertificate:
    async def test_auto_issue_new_certificate_returns_201(
        self, client, mock_cert_service,
    ):
        user_id = uuid4()
        course_id = uuid4()
        cert = _make_certificate(user_id, course_id)
        mock_cert_service.auto_issue_certificate.return_value = (cert, True)

        resp = await client.post(
            "/internal/certificates/auto-issue",
            json={
                "user_id": str(user_id),
                "course_id": str(course_id),
                "student_name": "John Doe",
                "course_title": "Python 101",
            },
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["certificate_number"] == cert.certificate_number
        mock_cert_service.auto_issue_certificate.assert_called_once_with(
            user_id=user_id,
            course_id=course_id,
            student_name="John Doe",
            course_title="Python 101",
        )

    async def test_auto_issue_existing_certificate_returns_200(
        self, client, mock_cert_service,
    ):
        user_id = uuid4()
        course_id = uuid4()
        cert = _make_certificate(user_id, course_id)
        mock_cert_service.auto_issue_certificate.return_value = (cert, False)

        resp = await client.post(
            "/internal/certificates/auto-issue",
            json={
                "user_id": str(user_id),
                "course_id": str(course_id),
                "student_name": "John Doe",
                "course_title": "Python 101",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["certificate_number"] == cert.certificate_number
