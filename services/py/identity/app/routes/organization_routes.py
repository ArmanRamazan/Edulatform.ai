from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse, Response

from common.errors import AppError
from app.domain.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrgMemberCreate,
    OrgMemberResponse,
    PaginatedOrgMembersResponse,
)
from app.services.organization_service import OrganizationService

router = APIRouter(tags=["organizations"])


def _get_org_service() -> OrganizationService:
    from app.main import get_org_service
    return get_org_service()


def _get_current_user_id(authorization: Annotated[str, Header()]) -> UUID:
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm]
        )
        return UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


@router.post("/organizations", status_code=201)
async def create_organization(
    body: OrganizationCreate,
    current_user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[OrganizationService, Depends(_get_org_service)],
) -> JSONResponse:
    org = await service.create_organization(
        name=body.name, slug=body.slug, owner_user_id=current_user_id
    )
    return JSONResponse(
        status_code=201,
        content=OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            logo_url=org.logo_url,
            settings=org.settings,
            is_active=org.is_active,
            created_at=org.created_at,
        ).model_dump(mode="json"),
    )


@router.get("/organizations/me")
async def get_my_organizations(
    current_user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[OrganizationService, Depends(_get_org_service)],
) -> list[OrganizationResponse]:
    orgs = await service.get_my_organizations(current_user_id)
    return [
        OrganizationResponse(
            id=o.id,
            name=o.name,
            slug=o.slug,
            logo_url=o.logo_url,
            settings=o.settings,
            is_active=o.is_active,
            created_at=o.created_at,
        )
        for o in orgs
    ]


@router.get("/organizations/{org_id}")
async def get_organization(
    org_id: UUID,
    current_user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[OrganizationService, Depends(_get_org_service)],
) -> OrganizationResponse:
    org = await service.get_organization_for_member(org_id, current_user_id)
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        logo_url=org.logo_url,
        settings=org.settings,
        is_active=org.is_active,
        created_at=org.created_at,
    )


@router.post("/organizations/{org_id}/members", status_code=201)
async def add_member(
    org_id: UUID,
    body: OrgMemberCreate,
    current_user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[OrganizationService, Depends(_get_org_service)],
) -> JSONResponse:
    member = await service.invite_member(
        org_id, body.user_id, inviter_user_id=current_user_id, role=body.role
    )
    return JSONResponse(
        status_code=201,
        content=OrgMemberResponse(
            id=member.id,
            organization_id=member.organization_id,
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
        ).model_dump(mode="json"),
    )


@router.delete("/organizations/{org_id}/members/{user_id}", status_code=204)
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    current_user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[OrganizationService, Depends(_get_org_service)],
) -> Response:
    await service.remove_member(org_id, user_id, remover_user_id=current_user_id)
    return Response(status_code=204)


@router.get("/organizations/{org_id}/members")
async def get_members(
    org_id: UUID,
    current_user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[OrganizationService, Depends(_get_org_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedOrgMembersResponse:
    members = await service.get_members(org_id, current_user_id, limit=limit, offset=offset)
    return PaginatedOrgMembersResponse(
        items=[
            OrgMemberResponse(
                id=m.id,
                organization_id=m.organization_id,
                user_id=m.user_id,
                role=m.role,
                joined_at=m.joined_at,
            )
            for m in members
        ],
        total=len(members),
    )
