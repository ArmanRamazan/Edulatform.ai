from __future__ import annotations

import random
import string
from datetime import datetime, timezone
from uuid import UUID

from common.errors import ConflictError, NotFoundError
from app.domain.certificate import (
    Certificate,
    CertificateListResponse,
    CertificateResponse,
)
from app.repositories.certificate_repo import CertificateRepository


class CertificateService:
    def __init__(self, repo: CertificateRepository) -> None:
        self._repo = repo

    async def issue_certificate(
        self, user_id: UUID, course_id: UUID,
    ) -> Certificate:
        existing = await self._repo.get_by_user_and_course(user_id, course_id)
        if existing is not None:
            raise ConflictError("Certificate already issued for this course")

        certificate_number = self._generate_certificate_number()
        return await self._repo.create(
            user_id=user_id,
            course_id=course_id,
            certificate_number=certificate_number,
        )

    async def get_my_certificates(self, user_id: UUID) -> CertificateListResponse:
        certs = await self._repo.get_by_user(user_id)
        return CertificateListResponse(
            certificates=[
                CertificateResponse(
                    id=c.id,
                    user_id=c.user_id,
                    course_id=c.course_id,
                    issued_at=c.issued_at,
                    certificate_number=c.certificate_number,
                )
                for c in certs
            ],
            total=len(certs),
        )

    async def get_certificate(self, certificate_id: UUID) -> Certificate:
        cert = await self._repo.get_by_id(certificate_id)
        if cert is None:
            raise NotFoundError("Certificate not found")
        return cert

    @staticmethod
    def _generate_certificate_number() -> str:
        year = datetime.now(timezone.utc).strftime("%Y")
        random_part = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )
        return f"CERT-{year}-{random_part}"
