from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError
from app.domain.certificate import (
    CertificateListResponse,
    CertificateResponse,
    IssueCertificateRequest,
)
from app.services.certificate_service import CertificateService

router = APIRouter(prefix="/certificates", tags=["certificates"])


def _get_certificate_service() -> CertificateService:
    from app.main import get_certificate_service
    return get_certificate_service()


def _get_current_user_claims(authorization: Annotated[str, Header()]) -> dict:
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm]
        )
        return {
            "user_id": UUID(payload["sub"]),
            "role": payload.get("role", "student"),
            "is_verified": payload.get("is_verified", False),
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


@router.post("/issue", response_model=CertificateResponse, status_code=201)
async def issue_certificate(
    body: IssueCertificateRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CertificateService, Depends(_get_certificate_service)],
) -> CertificateResponse:
    cert = await service.issue_certificate(
        user_id=claims["user_id"],
        course_id=body.course_id,
    )
    return CertificateResponse(
        id=cert.id,
        user_id=cert.user_id,
        course_id=cert.course_id,
        issued_at=cert.issued_at,
        certificate_number=cert.certificate_number,
    )


@router.get("/me", response_model=CertificateListResponse)
async def get_my_certificates(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CertificateService, Depends(_get_certificate_service)],
) -> CertificateListResponse:
    return await service.get_my_certificates(user_id=claims["user_id"])


@router.get("/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(
    certificate_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CertificateService, Depends(_get_certificate_service)],
) -> CertificateResponse:
    cert = await service.get_certificate(certificate_id)
    return CertificateResponse(
        id=cert.id,
        user_id=cert.user_id,
        course_id=cert.course_id,
        issued_at=cert.issued_at,
        certificate_number=cert.certificate_number,
    )
