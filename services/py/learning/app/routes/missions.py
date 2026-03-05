from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel

from common.errors import AppError
from app.domain.mission import Mission
from app.services.mission_service import MissionService

router = APIRouter(prefix="/missions", tags=["missions"])


def _get_mission_service() -> MissionService:
    from app.main import get_mission_service
    return get_mission_service()


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
            "token": token,
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


# --- Response models ---


class MissionResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    concept_id: UUID | None
    mission_type: str
    status: str
    blueprint: dict
    score: float | None
    mastery_delta: float | None
    started_at: str | None
    completed_at: str | None
    created_at: str


class MissionListResponse(BaseModel):
    missions: list[MissionResponse]


class StreakResponse(BaseModel):
    current_streak: int


class CompleteMissionRequest(BaseModel):
    session_id: str


def _to_response(m: Mission) -> MissionResponse:
    return MissionResponse(
        id=m.id,
        user_id=m.user_id,
        organization_id=m.organization_id,
        concept_id=m.concept_id,
        mission_type=m.mission_type,
        status=m.status,
        blueprint=m.blueprint,
        score=m.score,
        mastery_delta=m.mastery_delta,
        started_at=m.started_at.isoformat() if m.started_at else None,
        completed_at=m.completed_at.isoformat() if m.completed_at else None,
        created_at=m.created_at.isoformat(),
    )


@router.get("/today", response_model=MissionResponse)
async def get_today_mission(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[MissionService, Depends(_get_mission_service)],
    org_id: UUID = Query(...),
) -> MissionResponse:
    mission = await service.get_or_create_today(
        user_id=claims["user_id"],
        org_id=org_id,
        token=claims["token"],
    )
    return _to_response(mission)


@router.post("/{mission_id}/start", response_model=MissionResponse)
async def start_mission(
    mission_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[MissionService, Depends(_get_mission_service)],
) -> MissionResponse:
    mission = await service.start_mission(mission_id, claims["user_id"])
    return _to_response(mission)


@router.post("/{mission_id}/complete", response_model=MissionResponse)
async def complete_mission(
    mission_id: UUID,
    body: CompleteMissionRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[MissionService, Depends(_get_mission_service)],
) -> MissionResponse:
    mission = await service.complete_mission(
        mission_id=mission_id,
        user_id=claims["user_id"],
        session_id=body.session_id,
        token=claims["token"],
    )
    return _to_response(mission)


@router.get("/me", response_model=MissionListResponse)
async def get_my_missions(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[MissionService, Depends(_get_mission_service)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MissionListResponse:
    missions = await service.get_my_missions(
        user_id=claims["user_id"], limit=limit, offset=offset,
    )
    return MissionListResponse(missions=[_to_response(m) for m in missions])


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[MissionService, Depends(_get_mission_service)],
) -> StreakResponse:
    streak = await service.get_streak(claims["user_id"])
    return StreakResponse(current_streak=streak)
