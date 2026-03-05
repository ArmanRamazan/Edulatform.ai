from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.domain.certificate import AutoIssueCertificateRequest, CertificateResponse
from app.services.certificate_service import CertificateService

router = APIRouter(prefix="/internal/certificates", tags=["internal-certificates"])


def _get_certificate_service() -> CertificateService:
    from app.main import get_certificate_service
    return get_certificate_service()


@router.post("/auto-issue", response_model=CertificateResponse)
async def auto_issue_certificate(
    body: AutoIssueCertificateRequest,
    service: CertificateService = Depends(_get_certificate_service),
) -> CertificateResponse:
    cert, created = await service.auto_issue_certificate(
        user_id=body.user_id,
        course_id=body.course_id,
        student_name=body.student_name,
        course_title=body.course_title,
    )
    response = CertificateResponse(
        id=cert.id,
        user_id=cert.user_id,
        course_id=cert.course_id,
        issued_at=cert.issued_at,
        certificate_number=cert.certificate_number,
    )
    if created:
        from fastapi.responses import JSONResponse
        return JSONResponse(content=response.model_dump(mode="json"), status_code=201)
    return response
