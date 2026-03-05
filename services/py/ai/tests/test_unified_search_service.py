"""Tests for UnifiedSearchService — unified search orchestration."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.unified_search import (
    UnifiedSearchResult,
    InternalSearchResult,
    ExternalSearchResult,
)
from app.services.query_router import QueryRouter
from app.services.unified_search_service import UnifiedSearchService


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def mock_query_router():
    return MagicMock(spec=QueryRouter)


@pytest.fixture
def mock_http_client():
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_llm():
    mock = AsyncMock()
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


@pytest.fixture
def mock_credit_service():
    mock = AsyncMock()
    mock.check_and_consume.return_value = 5
    return mock


@pytest.fixture
def service(mock_http_client, mock_llm, mock_query_router):
    from app.config import Settings
    return UnifiedSearchService(
        http_client=mock_http_client,
        llm_client=mock_llm,
        query_router=mock_query_router,
        settings=Settings(),
    )


class TestSearchInternalOnly:
    """When query routes to 'internal', only RAG is called."""

    async def test_returns_internal_results_only(self, service, mock_query_router, mock_http_client, org_id):
        mock_query_router.classify.return_value = "internal"
        mock_http_client.post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "results": [
                    {"document_title": "Auth Guide", "source_path": "docs/auth.md", "content": "JWT auth flow"},
                ]
            },
        )

        result = await service.search("our auth flow", org_id=org_id, org_terms=["auth"])

        assert result.route == "internal"
        assert len(result.internal_results) == 1
        assert result.internal_results[0].title == "Auth Guide"
        assert result.external_results == []

    async def test_does_not_call_external(self, service, mock_query_router, mock_llm, org_id):
        mock_query_router.classify.return_value = "internal"
        mock_http_client = service._http
        mock_http_client.post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"results": []},
        )

        await service.search("internal docs", org_id=org_id)

        mock_llm.generate.assert_not_called()


class TestSearchExternalOnly:
    """When query routes to 'external', only LLM web grounding is called."""

    async def test_returns_external_results_only(self, service, mock_query_router, mock_llm, mock_http_client, org_id):
        mock_query_router.classify.return_value = "external"
        mock_llm.generate.return_value = (
            '[{"title": "React Docs", "url": "https://react.dev", "snippet": "React is a library"}]',
            10, 20,
        )

        result = await service.search("react hooks tutorial", org_id=org_id)

        assert result.route == "external"
        assert result.internal_results == []
        assert len(result.external_results) == 1
        assert result.external_results[0].title == "React Docs"
        assert result.external_results[0].url == "https://react.dev"

    async def test_does_not_call_rag(self, service, mock_query_router, mock_llm, mock_http_client, org_id):
        mock_query_router.classify.return_value = "external"
        mock_llm.generate.return_value = ("[]", 5, 5)

        await service.search("python tutorial", org_id=org_id)

        mock_http_client.post.assert_not_called()


class TestSearchBoth:
    """When query routes to 'both', both RAG and external are called."""

    async def test_returns_both_results(self, service, mock_query_router, mock_http_client, mock_llm, org_id):
        mock_query_router.classify.return_value = "both"
        mock_http_client.post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "results": [
                    {"document_title": "Our Redis", "source_path": "docs/redis.md", "content": "Redis config"},
                ]
            },
        )
        mock_llm.generate.return_value = (
            '[{"title": "Redis Docs", "url": "https://redis.io", "snippet": "Redis is a data store"}]',
            10, 20,
        )

        result = await service.search("how we use redis", org_id=org_id)

        assert result.route == "both"
        assert len(result.internal_results) == 1
        assert len(result.external_results) == 1

    async def test_internal_results_never_contain_external_data(self, service, mock_query_router, mock_http_client, mock_llm, org_id):
        mock_query_router.classify.return_value = "both"
        mock_http_client.post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "results": [
                    {"document_title": "Internal Doc", "source_path": "src/app.py", "content": "app code"},
                ]
            },
        )
        mock_llm.generate.return_value = (
            '[{"title": "External Doc", "url": "https://example.com", "snippet": "external content"}]',
            10, 20,
        )

        result = await service.search("event sourcing patterns", org_id=org_id)

        for r in result.internal_results:
            assert r.title != "External Doc"
        for r in result.external_results:
            assert r.title != "Internal Doc"


class TestSearchErrorHandling:
    """Graceful degradation when backends fail."""

    async def test_rag_failure_returns_empty_internal(self, service, mock_query_router, mock_http_client, mock_llm, org_id):
        mock_query_router.classify.return_value = "both"
        mock_http_client.post.side_effect = Exception("RAG unavailable")
        mock_llm.generate.return_value = (
            '[{"title": "Fallback", "url": "https://example.com", "snippet": "still works"}]',
            10, 20,
        )

        result = await service.search("how we use python", org_id=org_id)

        assert result.route == "both"
        assert result.internal_results == []
        assert len(result.external_results) == 1

    async def test_external_failure_returns_empty_external(self, service, mock_query_router, mock_http_client, mock_llm, org_id):
        mock_query_router.classify.return_value = "both"
        mock_http_client.post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "results": [
                    {"document_title": "Doc", "source_path": "x.md", "content": "content"},
                ]
            },
        )
        mock_llm.generate.side_effect = Exception("LLM unavailable")

        result = await service.search("how we use python", org_id=org_id)

        assert result.route == "both"
        assert len(result.internal_results) == 1
        assert result.external_results == []

    async def test_rag_non_200_returns_empty(self, service, mock_query_router, mock_http_client, org_id):
        mock_query_router.classify.return_value = "internal"
        mock_http_client.post.return_value = AsyncMock(status_code=500)

        result = await service.search("our API", org_id=org_id)

        assert result.internal_results == []

    async def test_malformed_llm_response_returns_empty(self, service, mock_query_router, mock_llm, org_id):
        mock_query_router.classify.return_value = "external"
        mock_llm.generate.return_value = ("not valid json at all", 5, 5)

        result = await service.search("react tutorial", org_id=org_id)

        assert result.external_results == []


class TestSearchOrgTerms:
    """Org terms are passed through to query router."""

    async def test_passes_org_terms_to_classifier(self, service, mock_query_router, mock_http_client, org_id):
        mock_query_router.classify.return_value = "internal"
        mock_http_client.post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"results": []},
        )

        await service.search("PaymentEngine flow", org_id=org_id, org_terms=["PaymentEngine"])

        mock_query_router.classify.assert_called_once_with("PaymentEngine flow", ["PaymentEngine"])


class TestSearchLimit:
    """Limit parameter is passed to RAG search."""

    async def test_passes_limit_to_rag(self, service, mock_query_router, mock_http_client, org_id):
        mock_query_router.classify.return_value = "internal"
        mock_http_client.post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"results": []},
        )

        await service.search("our API", org_id=org_id, limit=10)

        call_kwargs = mock_http_client.post.call_args
        assert call_kwargs.kwargs["json"]["limit"] == 10
