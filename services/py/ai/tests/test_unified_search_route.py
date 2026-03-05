"""Tests for POST /ai/search/unified route."""

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.domain.unified_search import (
    UnifiedSearchResult,
    InternalSearchResult,
    ExternalSearchResult,
)
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient
from app.services.credit_service import CreditService
from app.services.query_router import QueryRouter
from app.services.unified_search_service import UnifiedSearchService


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def mock_llm():
    mock = AsyncMock(spec=GeminiClient)
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


@pytest.fixture
def mock_unified_search_service():
    return AsyncMock(spec=UnifiedSearchService)


def _make_token(settings: Settings, user_id: str | None = None, tier: str = "free") -> str:
    payload = {
        "sub": user_id or str(uuid4()),
        "role": "student",
        "subscription_tier": tier,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
async def client(settings, mock_cache, mock_llm, mock_unified_search_service):
    import app.main as main_module

    main_module.app_settings = settings
    main_module._ai_service = main_module.AIService(mock_llm, mock_cache, settings)
    main_module._tutor_service = main_module.TutorService(mock_llm, mock_cache, settings)
    main_module._credit_service = CreditService(cache=mock_cache)
    main_module._unified_search_service = mock_unified_search_service

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestUnifiedSearchEndpoint:
    async def test_returns_unified_results(self, client, settings, mock_unified_search_service, mock_cache):
        mock_cache.get_credits_used.return_value = 0
        mock_cache.increment_credits.return_value = 1
        org_id = uuid4()
        mock_unified_search_service.search.return_value = UnifiedSearchResult(
            route="both",
            internal_results=[
                InternalSearchResult(title="Doc", source_path="x.md", content="content"),
            ],
            external_results=[
                ExternalSearchResult(title="Web", url="https://example.com", snippet="snippet"),
            ],
        )
        token = _make_token(settings)

        resp = await client.post(
            "/ai/search/unified",
            json={"query": "event sourcing", "org_id": str(org_id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["route"] == "both"
        assert len(data["internal_results"]) == 1
        assert len(data["external_results"]) == 1
        assert data["internal_results"][0]["title"] == "Doc"
        assert data["external_results"][0]["url"] == "https://example.com"

    async def test_consumes_credit(self, client, settings, mock_unified_search_service, mock_cache):
        mock_cache.get_credits_used.return_value = 0
        mock_cache.increment_credits.return_value = 1
        org_id = uuid4()
        mock_unified_search_service.search.return_value = UnifiedSearchResult(route="both")
        token = _make_token(settings)

        await client.post(
            "/ai/search/unified",
            json={"query": "test", "org_id": str(org_id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        mock_cache.increment_credits.assert_called_once()

    async def test_requires_auth(self, client):
        resp = await client.post(
            "/ai/search/unified",
            json={"query": "test", "org_id": str(uuid4())},
        )
        assert resp.status_code in (401, 422)

    async def test_invalid_token(self, client, settings):
        resp = await client.post(
            "/ai/search/unified",
            json={"query": "test", "org_id": str(uuid4())},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401

    async def test_passes_org_terms(self, client, settings, mock_unified_search_service, mock_cache):
        mock_cache.get_credits_used.return_value = 0
        mock_cache.increment_credits.return_value = 1
        org_id = uuid4()
        mock_unified_search_service.search.return_value = UnifiedSearchResult(route="internal")
        token = _make_token(settings)

        await client.post(
            "/ai/search/unified",
            json={
                "query": "PaymentEngine flow",
                "org_id": str(org_id),
                "org_terms": ["PaymentEngine"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        call_kwargs = mock_unified_search_service.search.call_args.kwargs
        assert call_kwargs["org_terms"] == ["PaymentEngine"]

    async def test_default_limit(self, client, settings, mock_unified_search_service, mock_cache):
        mock_cache.get_credits_used.return_value = 0
        mock_cache.increment_credits.return_value = 1
        org_id = uuid4()
        mock_unified_search_service.search.return_value = UnifiedSearchResult(route="both")
        token = _make_token(settings)

        await client.post(
            "/ai/search/unified",
            json={"query": "test", "org_id": str(org_id)},
            headers={"Authorization": f"Bearer {token}"},
        )

        call_kwargs = mock_unified_search_service.search.call_args.kwargs
        assert call_kwargs["limit"] == 5
