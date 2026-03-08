from __future__ import annotations

import hashlib
import hmac
import time
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Form, Header, Query, Request
from fastapi.responses import JSONResponse

from common.errors import AppError, ForbiddenError, NotFoundError
from app.domain.slack import (
    SlackCommandResponse,
    SlackConfigCreate,
    SlackConfigDeleteRequest,
    SlackConfigDeleteResponse,
    SlackConfigResponse,
    SlackReminderResponse,
)
from app.repositories.slack_config_repo import SlackConfigRepository
from app.services.slack_reminder_service import SlackReminderService
from app.services.slack_search_service import SlackSearchService

router = APIRouter(prefix="/slack", tags=["slack"])


def _get_slack_reminder_service() -> SlackReminderService:
    from app.main import get_slack_reminder_service
    return get_slack_reminder_service()


def _get_slack_search_service() -> SlackSearchService:
    from app.main import get_slack_search_service
    return get_slack_search_service()


def _get_slack_config_repo() -> SlackConfigRepository:
    from app.main import get_slack_config_repo
    return get_slack_config_repo()


def _get_current_user_claims(authorization: Annotated[str, Header()]) -> dict:
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm]
        )
        org_raw = payload.get("organization_id")
        return {
            "user_id": UUID(payload["sub"]),
            "role": payload.get("role", "student"),
            "is_verified": payload.get("is_verified", False),
            "organization_id": UUID(org_raw) if org_raw else None,
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


def _verify_slack_signature(
    signing_secret: str,
    timestamp: str,
    body: bytes,
    signature: str,
) -> bool:
    """HMAC-SHA256 verification per Slack docs."""
    sig_basestring = f"v0:{timestamp}:{body.decode()}"
    computed = "v0=" + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


@router.post("/commands", response_model=SlackCommandResponse)
async def handle_slack_command(
    request: Request,
    x_slack_request_timestamp: Annotated[str | None, Header()] = None,
    x_slack_signature: Annotated[str | None, Header()] = None,
    search_service: SlackSearchService = Depends(_get_slack_search_service),
) -> SlackCommandResponse:
    from app.main import app_settings

    if not x_slack_request_timestamp or not x_slack_signature:
        raise ForbiddenError("Missing Slack signature headers")

    body = await request.body()

    if not _verify_slack_signature(
        app_settings.slack_signing_secret,
        x_slack_request_timestamp,
        body,
        x_slack_signature,
    ):
        raise ForbiddenError("Invalid Slack signature")

    form = await request.form()
    text = str(form.get("text", "")).strip()

    if text.lower().startswith("search "):
        query = text[7:].strip()
        result = await search_service.search(query, org_id=None)
        return SlackCommandResponse(text=result)

    help_text = (
        "Available commands:\n"
        "• `search <query>` — Search the knowledge base\n"
    )
    return SlackCommandResponse(text=help_text)


@router.post("/reminders/send", response_model=SlackReminderResponse)
async def send_mission_reminders(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[SlackReminderService, Depends(_get_slack_reminder_service)],
) -> SlackReminderResponse:
    if claims["role"] != "admin":
        raise ForbiddenError("Only admins can send Slack reminders")
    stats = await service.send_mission_reminders()
    return SlackReminderResponse(**stats)


@router.post("/config", response_model=SlackConfigResponse, status_code=201)
async def create_slack_config(
    body: SlackConfigCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    repo: Annotated[SlackConfigRepository, Depends(_get_slack_config_repo)],
) -> SlackConfigResponse:
    if claims["role"] != "admin":
        raise ForbiddenError("Only admins can manage Slack config")
    config = await repo.create(
        org_id=body.org_id,
        webhook_url=body.webhook_url,
        channel=body.channel,
    )
    return SlackConfigResponse.from_entity(config)


@router.get("/config", response_model=SlackConfigResponse)
async def get_slack_config(
    org_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    repo: Annotated[SlackConfigRepository, Depends(_get_slack_config_repo)],
) -> SlackConfigResponse:
    if claims["role"] != "admin":
        raise ForbiddenError("Only admins can view Slack config")
    config = await repo.get_by_org(org_id)
    if not config:
        raise NotFoundError("Slack config not found")
    return SlackConfigResponse.from_entity(config)


@router.post("/config/delete", response_model=SlackConfigDeleteResponse)
async def delete_slack_config(
    body: SlackConfigDeleteRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    repo: Annotated[SlackConfigRepository, Depends(_get_slack_config_repo)],
) -> SlackConfigDeleteResponse:
    if claims["role"] != "admin":
        raise ForbiddenError("Only admins can manage Slack config")
    deleted = await repo.delete(body.org_id)
    return SlackConfigDeleteResponse(deleted=deleted)
