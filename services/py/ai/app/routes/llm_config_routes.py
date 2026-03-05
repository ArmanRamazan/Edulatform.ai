"""Routes for per-organization LLM configuration management."""
from __future__ import annotations

import json
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from common.errors import AppError, ForbiddenError
from app.domain.llm_config import LLMConfig
from app.repositories.cache import AICache
from app.services.llm_resolver import LLMResolver, validate_llm_config

router = APIRouter(prefix="/ai/config", tags=["llm-config"])

_LLM_CONFIG_TTL = 300  # 5 minutes


def _get_llm_resolver() -> LLMResolver:
    from app.main import get_llm_resolver
    return get_llm_resolver()


def _get_cache() -> AICache:
    from app.main import get_cache
    return get_cache()


def _get_admin_claims(authorization: Annotated[str, Header()]) -> dict:
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm]
        )
        role = payload.get("role", "student")
        if role != "admin":
            raise ForbiddenError("Only admins can manage LLM configuration")
        return {
            "user_id": payload["sub"],
            "role": role,
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


class LLMConfigUpdateRequest(BaseModel):
    """Request body for updating LLM config."""

    internal_provider: str = "gemini"
    internal_model_url: str | None = None
    external_provider: str = "gemini"
    embedding_provider: str = "gemini"
    data_isolation: str = "standard"


@router.get("/llm/{org_id}")
async def get_llm_config(
    org_id: str,
    claims: Annotated[dict, Depends(_get_admin_claims)],
    cache: Annotated[AICache, Depends(_get_cache)],
) -> dict:
    """Get current LLM configuration for an organization."""
    raw = await cache.get_llm_config(org_id)
    if raw is None:
        return LLMConfig().to_dict()

    try:
        data = json.loads(raw)
        return LLMConfig.from_dict(data).to_dict()
    except (json.JSONDecodeError, TypeError):
        return LLMConfig().to_dict()


@router.put("/llm/{org_id}")
async def update_llm_config(
    org_id: str,
    body: LLMConfigUpdateRequest,
    claims: Annotated[dict, Depends(_get_admin_claims)],
    cache: Annotated[AICache, Depends(_get_cache)],
) -> dict:
    """Update LLM configuration for an organization."""
    config = LLMConfig(
        internal_provider=body.internal_provider,
        internal_model_url=body.internal_model_url,
        external_provider=body.external_provider,
        embedding_provider=body.embedding_provider,
        data_isolation=body.data_isolation,
    )

    validate_llm_config(config)

    await cache.set_llm_config(org_id, json.dumps(config.to_dict()), _LLM_CONFIG_TTL)

    return config.to_dict()


@router.post("/llm/{org_id}/test")
async def test_llm_connection(
    org_id: str,
    body: LLMConfigUpdateRequest,
    claims: Annotated[dict, Depends(_get_admin_claims)],
    resolver: Annotated[LLMResolver, Depends(_get_llm_resolver)],
) -> dict:
    """Test connection to the configured LLM provider."""
    config = LLMConfig(
        internal_provider=body.internal_provider,
        internal_model_url=body.internal_model_url,
        external_provider=body.external_provider,
        embedding_provider=body.embedding_provider,
        data_isolation=body.data_isolation,
    )

    provider = resolver.resolve_from_config(config)

    try:
        text, tokens_in, tokens_out = await provider.complete("ping")
        return {
            "success": True,
            "response_preview": text[:100],
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }
