from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Callable
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from common.errors import AppError, ForbiddenError
from app.services.knowledge_base_service import KnowledgeBaseService


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


def create_knowledge_base_router(
    get_service: Callable[[], KnowledgeBaseService],
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(tags=["knowledge-base"])

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

    @router.get("/kb/{org_id}/stats")
    async def get_stats(
        org_id: UUID,
        claims: dict = Depends(_get_claims),
    ) -> dict:
        service = get_service()
        stats = await service.get_stats(org_id)
        return asdict(stats)

    @router.get("/kb/{org_id}/sources")
    async def list_sources(
        org_id: UUID,
        claims: dict = Depends(_get_claims),
    ) -> list[dict]:
        service = get_service()
        docs = await service.list_sources(org_id)
        return [
            {
                "id": str(d.id),
                "organization_id": str(d.organization_id),
                "source_type": d.source_type,
                "source_path": d.source_path,
                "title": d.title,
                "metadata": d.metadata,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ]

    @router.get("/kb/{org_id}/concepts")
    async def get_concept_graph(
        org_id: UUID,
        claims: dict = Depends(_get_claims),
    ) -> dict:
        service = get_service()
        return await service.get_concept_graph(org_id)

    @router.post("/kb/{org_id}/search")
    async def search(
        org_id: UUID,
        body: SearchRequest,
        claims: dict = Depends(_get_claims),
    ) -> list[dict]:
        service = get_service()
        results = await service.search(org_id, body.query, limit=body.limit)
        return [
            {
                "chunk_id": str(r.chunk_id),
                "content": r.content,
                "similarity": r.similarity,
                "document_title": r.document_title,
                "source_type": r.source_type,
                "source_path": r.source_path,
                "metadata": r.metadata,
            }
            for r in results
        ]

    @router.post("/kb/{org_id}/refresh/{document_id}")
    async def refresh_source(
        org_id: UUID,
        document_id: UUID,
        claims: dict = Depends(_get_claims),
    ) -> dict:
        if claims["role"] != "admin":
            raise ForbiddenError()
        service = get_service()
        doc = await service.refresh_source(document_id)
        return {
            "id": str(doc.id),
            "organization_id": str(doc.organization_id),
            "source_type": doc.source_type,
            "source_path": doc.source_path,
            "title": doc.title,
            "metadata": doc.metadata,
            "created_at": doc.created_at.isoformat(),
        }

    return router
