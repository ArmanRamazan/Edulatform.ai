"""Routes for unified search."""

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError
from app.domain.models import (
    UnifiedSearchRequest,
    UnifiedSearchResponse,
    InternalSearchResultResponse,
    ExternalSearchResultResponse,
)
from app.services.credit_service import CreditService
from app.services.unified_search_service import UnifiedSearchService

router = APIRouter(prefix="/ai", tags=["search"])


def _get_unified_search_service() -> UnifiedSearchService:
    from app.main import get_unified_search_service
    return get_unified_search_service()


def _get_credit_service() -> CreditService:
    from app.main import get_credit_service
    return get_credit_service()


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
            "subscription_tier": payload.get("subscription_tier", "free"),
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


@router.post("/search/unified", response_model=UnifiedSearchResponse)
async def unified_search(
    body: UnifiedSearchRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[UnifiedSearchService, Depends(_get_unified_search_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> UnifiedSearchResponse:
    await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )

    result = await service.search(
        query=body.query,
        org_id=body.org_id,
        org_terms=body.org_terms,
        limit=body.limit,
    )

    return UnifiedSearchResponse(
        route=result.route,
        internal_results=[
            InternalSearchResultResponse(
                title=r.title, source_path=r.source_path, content=r.content,
            )
            for r in result.internal_results
        ],
        external_results=[
            ExternalSearchResultResponse(
                title=r.title, url=r.url, snippet=r.snippet,
            )
            for r in result.external_results
        ],
    )
