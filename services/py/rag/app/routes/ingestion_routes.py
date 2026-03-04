from __future__ import annotations

from typing import Annotated, Callable
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel

from common.errors import AppError, ForbiddenError, NotFoundError
from app.domain.document import Document
from app.services.ingestion_service import IngestionService


class IngestRequest(BaseModel):
    org_id: UUID
    source_type: str
    source_path: str
    title: str
    content: str


class DocumentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    source_type: str
    source_path: str
    title: str
    metadata: dict
    created_at: str


def _to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        organization_id=doc.organization_id,
        source_type=doc.source_type,
        source_path=doc.source_path,
        title=doc.title,
        metadata=doc.metadata,
        created_at=doc.created_at.isoformat(),
    )


def create_ingestion_router(
    get_service: Callable[[], IngestionService],
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(tags=["documents"])

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

    @router.post("/documents", status_code=201)
    async def create_document(
        body: IngestRequest,
        claims: dict = Depends(_get_claims),
    ) -> DocumentResponse:
        if claims["role"] not in ("admin", "teacher"):
            raise ForbiddenError("Only admin or teacher can ingest documents")
        service = get_service()
        doc = await service.ingest(
            org_id=body.org_id,
            source_type=body.source_type,
            source_path=body.source_path,
            title=body.title,
            content=body.content,
        )
        return _to_response(doc)

    @router.get("/documents")
    async def list_documents(
        org_id: UUID = Query(...),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        claims: dict = Depends(_get_claims),
    ) -> list[DocumentResponse]:
        service = get_service()
        docs = await service.get_documents_by_org(org_id, limit, offset)
        return [_to_response(d) for d in docs]

    @router.delete("/documents/{document_id}", status_code=204)
    async def delete_document(
        document_id: UUID,
        claims: dict = Depends(_get_claims),
    ) -> Response:
        if claims["role"] != "admin":
            raise ForbiddenError("Only admin can delete documents")
        service = get_service()
        deleted = await service.delete(document_id)
        if not deleted:
            raise NotFoundError("Document not found")
        return Response(status_code=204)

    return router
