from __future__ import annotations

from typing import Annotated, Callable
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from common.errors import AppError, ForbiddenError
from app.adapters.github_adapter import GitHubAdapter
from app.services.ingestion_service import IngestionService


class GitHubIndexRequest(BaseModel):
    org_id: UUID
    owner: str
    repo: str
    branch: str = "main"
    extensions: list[str] = Field(default_factory=lambda: [".py", ".ts", ".md", ".yaml"])


class GitHubIndexResponse(BaseModel):
    indexed_files_count: int


def create_github_router(
    get_github_adapter: Callable[[], GitHubAdapter],
    get_ingestion_service: Callable[[], IngestionService],
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(tags=["sources"])

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

    @router.post("/sources/github")
    async def index_github_repo(
        body: GitHubIndexRequest,
        claims: dict = Depends(_get_claims),
    ) -> GitHubIndexResponse:
        if claims["role"] != "admin":
            raise ForbiddenError("Only admin can index GitHub repositories")

        adapter = get_github_adapter()
        ingestion = get_ingestion_service()
        count = await adapter.index_repository(
            org_id=body.org_id,
            owner=body.owner,
            repo=body.repo,
            branch=body.branch,
            extensions=body.extensions,
            ingestion_service=ingestion,
        )
        return GitHubIndexResponse(indexed_files_count=count)

    return router
