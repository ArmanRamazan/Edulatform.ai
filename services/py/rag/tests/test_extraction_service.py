from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import json

import pytest
import httpx

from app.services.extraction_service import ExtractionService
from app.domain.extraction import ExtractedConcept


@pytest.fixture
def concept_store():
    store = AsyncMock()
    store.upsert_concept.return_value = uuid4()
    store.add_relationship.return_value = None
    return store


@pytest.fixture
def http_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def settings():
    s = MagicMock()
    s.openai_api_key = "test-api-key"
    return s


@pytest.fixture
def service(concept_store, http_client, settings):
    return ExtractionService(
        concept_store=concept_store,
        http_client=http_client,
        settings=settings,
    )


def _gemini_response(concepts: list[dict]) -> httpx.Response:
    """Build a mock Gemini API response with concept JSON."""
    content = json.dumps(concepts)
    body = {
        "candidates": [
            {"content": {"parts": [{"text": content}]}}
        ],
    }
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = body
    return resp


def _gemini_response_with_fences(concepts: list[dict]) -> httpx.Response:
    """Build a response wrapped in markdown code fences."""
    content = "```json\n" + json.dumps(concepts) + "\n```"
    body = {
        "candidates": [
            {"content": {"parts": [{"text": content}]}}
        ],
    }
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = body
    return resp


class TestExtractConcepts:
    async def test_parses_concepts_from_llm_response(self, service, http_client):
        concepts_data = [
            {
                "name": "Dependency Injection",
                "description": "A design pattern for decoupling components",
                "related_concepts": ["Inversion of Control"],
            },
            {
                "name": "Inversion of Control",
                "description": "A principle where control flow is inverted",
                "related_concepts": ["Dependency Injection"],
            },
        ]
        http_client.post.return_value = _gemini_response(concepts_data)
        doc_id = uuid4()

        result = await service.extract_concepts(doc_id, "Some document about DI patterns.")

        assert len(result) == 2
        assert isinstance(result[0], ExtractedConcept)
        assert result[0].name == "Dependency Injection"
        assert result[0].source_document_id == doc_id
        assert "Inversion of Control" in result[0].related_concepts

    async def test_strips_markdown_fences(self, service, http_client):
        concepts_data = [
            {
                "name": "FastAPI",
                "description": "A modern Python web framework",
                "related_concepts": [],
            },
        ]
        http_client.post.return_value = _gemini_response_with_fences(concepts_data)

        result = await service.extract_concepts(uuid4(), "FastAPI docs.")
        assert len(result) == 1
        assert result[0].name == "FastAPI"

    async def test_calls_gemini_api_with_correct_params(self, service, http_client, settings):
        http_client.post.return_value = _gemini_response([])

        await service.extract_concepts(uuid4(), "Test content")

        http_client.post.assert_called_once()
        call_args = http_client.post.call_args
        assert "generativelanguage.googleapis.com" in call_args[0][0]
        assert "key" in call_args[1].get("params", {})

    async def test_returns_empty_on_invalid_json(self, service, http_client):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "not valid json at all"}]}}
            ],
        }
        http_client.post.return_value = resp

        result = await service.extract_concepts(uuid4(), "Some content")
        assert result == []

    async def test_returns_empty_on_api_error(self, service, http_client):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 500
        resp.text = "Internal Server Error"
        http_client.post.return_value = resp

        result = await service.extract_concepts(uuid4(), "Some content")
        assert result == []

    async def test_returns_empty_on_http_exception(self, service, http_client):
        http_client.post.side_effect = httpx.HTTPError("connection failed")

        result = await service.extract_concepts(uuid4(), "Some content")
        assert result == []


class TestExtractFromCode:
    async def test_extracts_code_concepts(self, service, http_client):
        concepts_data = [
            {
                "name": "UserRepository",
                "description": "Repository class for user persistence",
                "related_concepts": ["Repository Pattern"],
            },
        ]
        http_client.post.return_value = _gemini_response(concepts_data)

        result = await service.extract_from_code(
            uuid4(), "class UserRepository:\n    pass", "python"
        )
        assert len(result) == 1
        assert result[0].name == "UserRepository"

    async def test_includes_language_in_prompt(self, service, http_client):
        http_client.post.return_value = _gemini_response([])

        await service.extract_from_code(uuid4(), "fn main() {}", "rust")

        call_args = http_client.post.call_args
        payload = call_args[1].get("json") or call_args[0][1]
        prompt_text = str(payload)
        assert "rust" in prompt_text.lower()


class TestStoreExtracted:
    async def test_stores_concepts_and_relationships(self, service, concept_store, http_client):
        concept_a_id = uuid4()
        concept_b_id = uuid4()
        concept_store.upsert_concept.side_effect = [concept_a_id, concept_b_id]

        concepts_data = [
            {
                "name": "Concept A",
                "description": "First concept",
                "related_concepts": ["Concept B"],
            },
            {
                "name": "Concept B",
                "description": "Second concept",
                "related_concepts": ["Concept A"],
            },
        ]
        http_client.post.return_value = _gemini_response(concepts_data)

        org_id = uuid4()
        doc_id = uuid4()
        await service.extract_and_store(org_id, doc_id, "Content about concepts.")

        assert concept_store.upsert_concept.call_count == 2
        # Relationships should be created
        assert concept_store.add_relationship.call_count >= 1

    async def test_extract_and_store_handles_extraction_failure(self, service, concept_store, http_client):
        http_client.post.side_effect = httpx.HTTPError("fail")

        org_id = uuid4()
        doc_id = uuid4()
        # Should not raise
        await service.extract_and_store(org_id, doc_id, "Content")

        concept_store.upsert_concept.assert_not_called()
