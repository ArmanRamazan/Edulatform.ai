from __future__ import annotations

from datetime import datetime
from typing import Annotated, Callable
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from common.errors import AppError, ForbiddenError
from app.services.github_connect_service import GitHubConnectService


class GitHubConnectRequest(BaseModel):
    org_id: UUID
    repo_url: str
    branch: str = "main"


class GitHubConnectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    repo_url: str
    branch: str
    last_synced_at: datetime | None
    created_at: datetime
    ingested_count: int


class WebhookResponse(BaseModel):
    processed_files: int


def create_github_connect_router(
    get_connect_service: Callable[[], GitHubConnectService],
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(tags=["github"])

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

    @router.post("/github/connect")
    async def connect_repo(
        body: GitHubConnectRequest,
        claims: dict = Depends(_get_claims),
    ) -> GitHubConnectResponse:
        if claims["role"] != "admin":
            raise ForbiddenError("Only admin can connect GitHub repositories")

        service = get_connect_service()
        repo_entity, count = await service.connect(
            org_id=body.org_id,
            repo_url=body.repo_url,
            branch=body.branch,
        )
        return GitHubConnectResponse(
            id=repo_entity.id,
            organization_id=repo_entity.organization_id,
            repo_url=repo_entity.repo_url,
            branch=repo_entity.branch,
            last_synced_at=repo_entity.last_synced_at,
            created_at=repo_entity.created_at,
            ingested_count=count,
        )

    @router.post("/github/webhook")
    async def github_webhook(
        body: dict,
        x_github_event: Annotated[str | None, Header()] = None,
    ) -> WebhookResponse:
        if x_github_event != "push":
            return WebhookResponse(processed_files=0)

        service = get_connect_service()
        count = await service.process_webhook(payload=body)
        return WebhookResponse(processed_files=count)

    return router
