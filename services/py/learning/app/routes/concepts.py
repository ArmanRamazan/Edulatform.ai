from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError
from app.domain.concept import (
    ConceptCreate,
    ConceptUpdate,
    ConceptResponse,
    PrerequisiteAdd,
    CourseGraphResponse,
    CourseMasteryResponse,
)
from app.services.concept_service import ConceptService

router = APIRouter(prefix="/concepts", tags=["concepts"])


def _get_concept_service() -> ConceptService:
    from app.main import get_concept_service
    return get_concept_service()


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


@router.post("", response_model=ConceptResponse, status_code=201)
async def create_concept(
    body: ConceptCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[ConceptService, Depends(_get_concept_service)],
) -> ConceptResponse:
    concept = await service.create_concept(
        teacher_id=claims["user_id"],
        role=claims["role"],
        is_verified=claims["is_verified"],
        course_id=body.course_id,
        name=body.name,
        description=body.description,
        lesson_id=body.lesson_id,
        parent_id=body.parent_id,
        order=body.order,
    )
    return ConceptResponse(
        id=concept.id, course_id=concept.course_id, lesson_id=concept.lesson_id,
        name=concept.name, description=concept.description,
        parent_id=concept.parent_id, order=concept.order,
        created_at=concept.created_at,
    )


@router.put("/{concept_id}", response_model=ConceptResponse)
async def update_concept(
    concept_id: UUID,
    body: ConceptUpdate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[ConceptService, Depends(_get_concept_service)],
) -> ConceptResponse:
    kwargs = body.model_dump(exclude_unset=True)
    concept = await service.update_concept(
        concept_id=concept_id,
        teacher_id=claims["user_id"],
        role=claims["role"],
        is_verified=claims["is_verified"],
        **kwargs,
    )
    return ConceptResponse(
        id=concept.id, course_id=concept.course_id, lesson_id=concept.lesson_id,
        name=concept.name, description=concept.description,
        parent_id=concept.parent_id, order=concept.order,
        created_at=concept.created_at,
    )


@router.delete("/{concept_id}", status_code=204)
async def delete_concept(
    concept_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[ConceptService, Depends(_get_concept_service)],
) -> None:
    await service.delete_concept(
        concept_id=concept_id,
        teacher_id=claims["user_id"],
        role=claims["role"],
        is_verified=claims["is_verified"],
    )


@router.post("/{concept_id}/prerequisites", status_code=201)
async def add_prerequisite(
    concept_id: UUID,
    body: PrerequisiteAdd,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[ConceptService, Depends(_get_concept_service)],
) -> dict[str, str]:
    await service.add_prerequisite(
        concept_id=concept_id,
        prerequisite_id=body.prerequisite_id,
        role=claims["role"],
        is_verified=claims["is_verified"],
    )
    return {"status": "ok"}


@router.delete("/{concept_id}/prerequisites/{prerequisite_id}", status_code=204)
async def remove_prerequisite(
    concept_id: UUID,
    prerequisite_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[ConceptService, Depends(_get_concept_service)],
) -> None:
    await service.remove_prerequisite(
        concept_id=concept_id,
        prerequisite_id=prerequisite_id,
        role=claims["role"],
        is_verified=claims["is_verified"],
    )


@router.get("/course/{course_id}", response_model=CourseGraphResponse)
async def get_course_graph(
    course_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[ConceptService, Depends(_get_concept_service)],
) -> CourseGraphResponse:
    return await service.get_course_graph(course_id)


@router.get("/mastery/course/{course_id}", response_model=CourseMasteryResponse)
async def get_course_mastery(
    course_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[ConceptService, Depends(_get_concept_service)],
) -> CourseMasteryResponse:
    return await service.get_course_mastery(claims["user_id"], course_id)
