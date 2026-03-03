from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError
from app.domain.pretest import (
    AnswerSubmit,
    PretestStartResponse,
    AnswerNextResponse,
    PretestResultsResponse,
)
from app.services.pretest_service import PretestService

router = APIRouter(prefix="/pretests", tags=["pretests"])


def _get_pretest_service() -> PretestService:
    from app.main import get_pretest_service
    return get_pretest_service()


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


@router.post("/course/{course_id}/start", response_model=PretestStartResponse, status_code=201)
async def start_pretest(
    course_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[PretestService, Depends(_get_pretest_service)],
) -> PretestStartResponse:
    result = await service.start_pretest(claims["user_id"], course_id)
    return PretestStartResponse(**result)


@router.post("/{pretest_id}/answer", response_model=AnswerNextResponse)
async def submit_answer(
    pretest_id: UUID,
    body: AnswerSubmit,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[PretestService, Depends(_get_pretest_service)],
) -> AnswerNextResponse:
    result = await service.answer_and_next(
        pretest_id, body.answer_id, body.answer, claims["user_id"]
    )
    return AnswerNextResponse(**result)


@router.get("/course/{course_id}/results", response_model=PretestResultsResponse)
async def get_results(
    course_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[PretestService, Depends(_get_pretest_service)],
) -> PretestResultsResponse:
    result = await service.get_results(claims["user_id"], course_id)
    return PretestResultsResponse(**result)
