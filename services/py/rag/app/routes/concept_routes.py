from __future__ import annotations

from typing import Annotated, Callable
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from common.errors import AppError, ForbiddenError
from app.repositories.concept_store import ConceptStoreRepository
from app.services.extraction_service import ExtractionService


class ExtractRequest(BaseModel):
    org_id: UUID


def create_concept_router(
    get_extraction_service: Callable[[], ExtractionService],
    get_concept_store: Callable[[], ConceptStoreRepository],
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(tags=["concepts"])

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

    @router.get("/concepts")
    async def get_concepts(
        org_id: UUID,
        claims: dict = Depends(_get_claims),
    ) -> list[dict]:
        store = get_concept_store()
        return await store.get_org_concepts(org_id)

    @router.post("/concepts/extract/{document_id}", status_code=202)
    async def extract_concepts(
        document_id: UUID,
        body: ExtractRequest,
        claims: dict = Depends(_get_claims),
    ) -> dict:
        if claims["role"] not in ("admin", "teacher"):
            raise ForbiddenError()
        service = get_extraction_service()
        await service.extract_and_store(
            org_id=body.org_id,
            document_id=document_id,
            content="",  # Will be fetched by the service if needed
        )
        return {"status": "accepted", "document_id": str(document_id)}

    return router
