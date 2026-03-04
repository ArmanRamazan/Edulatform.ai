from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.domain.wishlist import (
    WishlistAddRequest,
    WishlistCheckResponse,
    WishlistItemResponse,
    WishlistListResponse,
)
from app.routes.courses import _get_current_user_claims
from app.services.wishlist_service import WishlistService

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


def _get_wishlist_service() -> WishlistService:
    from app.main import get_wishlist_service
    return get_wishlist_service()


def _to_response(item: "WishlistItem") -> WishlistItemResponse:
    from app.domain.wishlist import WishlistItem
    return WishlistItemResponse(
        id=item.id,
        user_id=item.user_id,
        course_id=item.course_id,
        course_title=item.course_title,
        course_description=item.course_description,
        created_at=item.created_at,
    )


@router.post("", response_model=WishlistItemResponse, status_code=201)
async def add_to_wishlist(
    body: WishlistAddRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[WishlistService, Depends(_get_wishlist_service)],
) -> WishlistItemResponse:
    item = await service.add_to_wishlist(
        user_id=claims["user_id"],
        course_id=body.course_id,
    )
    return _to_response(item)


@router.delete("/{course_id}", status_code=204)
async def remove_from_wishlist(
    course_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[WishlistService, Depends(_get_wishlist_service)],
) -> Response:
    await service.remove_from_wishlist(
        user_id=claims["user_id"],
        course_id=course_id,
    )
    return Response(status_code=204)


@router.get("/me", response_model=WishlistListResponse)
async def get_my_wishlist(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[WishlistService, Depends(_get_wishlist_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WishlistListResponse:
    items, total = await service.get_my_wishlist(
        user_id=claims["user_id"],
        limit=limit,
        offset=offset,
    )
    return WishlistListResponse(
        items=[_to_response(i) for i in items],
        total=total,
    )


@router.get("/check/{course_id}", response_model=WishlistCheckResponse)
async def check_in_wishlist(
    course_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[WishlistService, Depends(_get_wishlist_service)],
) -> WishlistCheckResponse:
    in_wishlist = await service.is_in_wishlist(
        user_id=claims["user_id"],
        course_id=course_id,
    )
    return WishlistCheckResponse(in_wishlist=in_wishlist)
