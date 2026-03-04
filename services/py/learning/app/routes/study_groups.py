from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.study_group import (
    CreateStudyGroupRequest,
    GroupMemberResponse,
    MemberListResponse,
    StudyGroupListResponse,
    StudyGroupResponse,
)
from app.services.study_group_service import StudyGroupService

router = APIRouter(prefix="/study-groups", tags=["study-groups"])


def _get_study_group_service() -> StudyGroupService:
    from app.main import get_study_group_service
    return get_study_group_service()


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


@router.post("", response_model=StudyGroupResponse, status_code=201)
async def create_group(
    body: CreateStudyGroupRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[StudyGroupService, Depends(_get_study_group_service)],
) -> StudyGroupResponse:
    group = await service.create_group(
        user_id=claims["user_id"],
        course_id=body.course_id,
        name=body.name,
        description=body.description,
    )
    return StudyGroupResponse(
        id=group.id,
        course_id=group.course_id,
        name=group.name,
        description=group.description,
        creator_id=group.creator_id,
        max_members=group.max_members,
        created_at=group.created_at,
    )


@router.get("/course/{course_id}", response_model=StudyGroupListResponse)
async def get_course_groups(
    course_id: UUID,
    service: Annotated[StudyGroupService, Depends(_get_study_group_service)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> StudyGroupListResponse:
    return await service.get_course_groups(course_id, limit=limit, offset=offset)


@router.post("/{group_id}/join", response_model=GroupMemberResponse, status_code=201)
async def join_group(
    group_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[StudyGroupService, Depends(_get_study_group_service)],
) -> GroupMemberResponse:
    member = await service.join_group(user_id=claims["user_id"], group_id=group_id)
    return GroupMemberResponse(
        id=member.id,
        group_id=member.group_id,
        user_id=member.user_id,
        joined_at=member.joined_at,
    )


@router.delete("/{group_id}/leave", status_code=204)
async def leave_group(
    group_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[StudyGroupService, Depends(_get_study_group_service)],
) -> None:
    await service.leave_group(user_id=claims["user_id"], group_id=group_id)


@router.get("/{group_id}/members", response_model=MemberListResponse)
async def get_members(
    group_id: UUID,
    service: Annotated[StudyGroupService, Depends(_get_study_group_service)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MemberListResponse:
    return await service.get_members(group_id, limit=limit, offset=offset)


@router.get("/me", response_model=list[StudyGroupResponse])
async def get_my_groups(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[StudyGroupService, Depends(_get_study_group_service)],
) -> list[StudyGroupResponse]:
    groups = await service.get_my_groups(user_id=claims["user_id"])
    return [
        StudyGroupResponse(
            id=g.id,
            course_id=g.course_id,
            name=g.name,
            description=g.description,
            creator_id=g.creator_id,
            max_members=g.max_members,
            created_at=g.created_at,
        )
        for g in groups
    ]
