from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.certificate import Certificate
from app.repositories.certificate_repo import CertificateRepository
from app.services.certificate_service import CertificateService

from common.errors import ConflictError, NotFoundError


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def mock_cert_repo():
    return AsyncMock(spec=CertificateRepository)


@pytest.fixture
def cert_service(mock_cert_repo):
    return CertificateService(repo=mock_cert_repo)


def _make_certificate(
    user_id,
    course_id,
    certificate_number: str = "CERT-2026-A1B2C3",
) -> Certificate:
    return Certificate(
        id=uuid4(),
        user_id=user_id,
        course_id=course_id,
        issued_at=datetime.now(timezone.utc),
        certificate_number=certificate_number,
        template_data={},
    )


class TestIssueCertificate:
    async def test_issues_certificate_successfully(
        self, cert_service, mock_cert_repo, user_id, course_id,
    ):
        mock_cert_repo.get_by_user_and_course.return_value = None
        cert = _make_certificate(user_id, course_id)
        mock_cert_repo.create.return_value = cert

        result = await cert_service.issue_certificate(user_id, course_id)

        assert result.user_id == user_id
        assert result.course_id == course_id
        mock_cert_repo.get_by_user_and_course.assert_awaited_once_with(user_id, course_id)
        mock_cert_repo.create.assert_awaited_once()

    async def test_issue_generates_certificate_number_format(
        self, cert_service, mock_cert_repo, user_id, course_id,
    ):
        mock_cert_repo.get_by_user_and_course.return_value = None
        cert = _make_certificate(user_id, course_id)
        mock_cert_repo.create.return_value = cert

        await cert_service.issue_certificate(user_id, course_id)

        call_args = mock_cert_repo.create.call_args
        cert_number = call_args.kwargs.get("certificate_number") or call_args[0][2]
        assert cert_number.startswith("CERT-")
        # Format: CERT-YYYY-XXXXXX
        parts = cert_number.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 4  # year
        assert len(parts[2]) == 6  # random alphanumeric

    async def test_issue_duplicate_raises_conflict(
        self, cert_service, mock_cert_repo, user_id, course_id,
    ):
        existing = _make_certificate(user_id, course_id)
        mock_cert_repo.get_by_user_and_course.return_value = existing

        with pytest.raises(ConflictError, match="already issued"):
            await cert_service.issue_certificate(user_id, course_id)

        mock_cert_repo.create.assert_not_awaited()


class TestGetMyCertificates:
    async def test_returns_certificates_list(
        self, cert_service, mock_cert_repo, user_id, course_id,
    ):
        certs = [
            _make_certificate(user_id, course_id),
            _make_certificate(user_id, uuid4()),
        ]
        mock_cert_repo.get_by_user.return_value = certs

        result = await cert_service.get_my_certificates(user_id)

        assert result.total == 2
        assert len(result.certificates) == 2
        mock_cert_repo.get_by_user.assert_awaited_once_with(user_id)

    async def test_returns_empty_list(
        self, cert_service, mock_cert_repo, user_id,
    ):
        mock_cert_repo.get_by_user.return_value = []

        result = await cert_service.get_my_certificates(user_id)

        assert result.total == 0
        assert result.certificates == []


class TestGetCertificate:
    async def test_returns_certificate_by_id(
        self, cert_service, mock_cert_repo, user_id, course_id,
    ):
        cert = _make_certificate(user_id, course_id)
        mock_cert_repo.get_by_id.return_value = cert

        result = await cert_service.get_certificate(cert.id)

        assert result.id == cert.id
        assert result.certificate_number == cert.certificate_number
        mock_cert_repo.get_by_id.assert_awaited_once_with(cert.id)

    async def test_not_found_raises(
        self, cert_service, mock_cert_repo,
    ):
        cert_id = uuid4()
        mock_cert_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="Certificate not found"):
            await cert_service.get_certificate(cert_id)
