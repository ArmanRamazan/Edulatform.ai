from __future__ import annotations

from typing import Annotated, Callable
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from common.errors import AppError
from app.domain.search import SearchResult
from app.services.search_service import SearchService


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    org_id: UUID
    limit: int = Field(5, ge=1, le=20)


class SearchResultResponse(BaseModel):
    chunk_id: UUID
    content: str
    similarity: float
    document_title: str
    source_type: str
    source_path: str
    metadata: dict


class SearchResponse(BaseModel):
    results: list[SearchResultResponse]
    query: str


def create_search_router(
    get_service: Callable[[], SearchService],
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(tags=["search"])

    def _get_claims(authorization: Annotated[str, Header()]) -> dict:
        if not authorization.startswith("Bearer "):
            raise AppError("Invalid authorization header", status_code=401)
        token = authorization[7:]
        try:
            payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
            return {
                "user_id": UUID(payload["sub"]),
                "role": payload.get("role", "student"),
            }
        except (jwt.PyJWTError, ValueError, KeyError) as exc:
            raise AppError("Invalid token", status_code=401) from exc

    @router.post("/search")
    async def search(
        body: SearchRequest,
        claims: dict = Depends(_get_claims),
    ) -> SearchResponse:
        service = get_service()
        results = await service.search(
            query=body.query,
            org_id=body.org_id,
            limit=body.limit,
        )
        return SearchResponse(
            results=[
                SearchResultResponse(
                    chunk_id=r.chunk_id,
                    content=r.content,
                    similarity=r.similarity,
                    document_title=r.document_title,
                    source_type=r.source_type,
                    source_path=r.source_path,
                    metadata=r.metadata,
                )
                for r in results
            ],
            query=body.query,
        )

    return router
