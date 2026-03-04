from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response

from common.errors import AppError
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/payments", tags=["invoices"])


def _get_invoice_service() -> InvoiceService:
    from app.main import get_invoice_service
    return get_invoice_service()


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


@router.get("/{payment_id}/invoice")
async def get_invoice(
    payment_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[InvoiceService, Depends(_get_invoice_service)],
) -> Response:
    pdf_bytes, filename = await service.generate_invoice(
        user_id=claims["user_id"],
        payment_id=payment_id,
        role=claims["role"],
        buyer_name="User",
        buyer_email="",
        course_title="Course",
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
