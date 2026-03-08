import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx

from app.services.slack_search_service import SlackSearchService


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def service(mock_http_client):
    return SlackSearchService(
        http_client=mock_http_client,
        ai_service_url="http://localhost:8006/api/ai",
        jwt_secret="test-secret",
    )


@pytest.mark.asyncio
async def test_search_returns_formatted_results(service, mock_http_client):
    org_id = uuid4()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"title": "Event Sourcing Guide", "snippet": "Learn how to use event sourcing."},
            {"title": "CQRS Pattern", "snippet": "Command Query Responsibility Segregation."},
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post = AsyncMock(return_value=mock_response)

    result = await service.search("event sourcing", org_id)

    assert "event sourcing" in result
    assert "Event Sourcing Guide" in result
    assert "CQRS Pattern" in result


@pytest.mark.asyncio
async def test_search_returns_error_message_on_failure(service, mock_http_client):
    mock_http_client.post = AsyncMock(side_effect=Exception("Connection error"))

    result = await service.search("distributed systems", None)

    assert "failed" in result.lower() or "error" in result.lower()


@pytest.mark.asyncio
async def test_search_passes_org_id_to_ai_service(service, mock_http_client):
    org_id = uuid4()
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post = AsyncMock(return_value=mock_response)

    await service.search("test query", org_id)

    mock_http_client.post.assert_called_once()
    call_kwargs = mock_http_client.post.call_args[1]
    assert call_kwargs["json"]["org_id"] == str(org_id)
    assert call_kwargs["json"]["query"] == "test query"


@pytest.mark.asyncio
async def test_search_with_none_org_id(service, mock_http_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post = AsyncMock(return_value=mock_response)

    result = await service.search("query", None)

    call_kwargs = mock_http_client.post.call_args[1]
    assert call_kwargs["json"]["org_id"] is None
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_search_formats_results_with_numbering(service, mock_http_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"title": "First Result", "snippet": "First snippet."},
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_http_client.post = AsyncMock(return_value=mock_response)

    result = await service.search("query", None)

    assert "1." in result or "1 " in result
    assert "First Result" in result
