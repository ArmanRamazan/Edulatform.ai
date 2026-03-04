from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.search_service import SearchService
from app.domain.search import SearchResult


@pytest.fixture
def search_repo():
    return AsyncMock()


@pytest.fixture
def embedding_client():
    client = AsyncMock()
    client.embed.return_value = [0.1, 0.2, 0.3]
    return client


@pytest.fixture
def service(search_repo, embedding_client):
    return SearchService(
        search_repo=search_repo,
        embedding_client=embedding_client,
    )


def _make_search_row(chunk_id=None):
    return {
        "id": chunk_id or uuid4(),
        "content": "Some relevant content.",
        "similarity": 0.92,
        "document_title": "Test Doc",
        "source_type": "text",
        "source_path": "/doc.md",
        "metadata": {},
        "chunk_index": 0,
    }


class TestSearch:
    async def test_embeds_query_and_searches(self, service, search_repo, embedding_client):
        search_repo.search.return_value = [_make_search_row()]

        results = await service.search("what is python?", uuid4(), limit=5)

        embedding_client.embed.assert_called_once_with("what is python?")
        search_repo.search.assert_called_once()
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)

    async def test_returns_search_results_with_correct_fields(self, service, search_repo):
        chunk_id = uuid4()
        search_repo.search.return_value = [_make_search_row(chunk_id=chunk_id)]

        results = await service.search("query", uuid4())
        result = results[0]
        assert result.chunk_id == chunk_id
        assert result.content == "Some relevant content."
        assert result.similarity == 0.92
        assert result.document_title == "Test Doc"
        assert result.source_type == "text"
        assert result.source_path == "/doc.md"

    async def test_passes_limit_to_repo(self, service, search_repo):
        search_repo.search.return_value = []

        await service.search("query", uuid4(), limit=10)
        _, kwargs = search_repo.search.call_args
        assert kwargs.get("limit", search_repo.search.call_args[0][2] if len(search_repo.search.call_args[0]) > 2 else None) == 10 or search_repo.search.call_args[0][2] == 10

    async def test_empty_results(self, service, search_repo):
        search_repo.search.return_value = []

        results = await service.search("query", uuid4())
        assert results == []

    async def test_passes_org_id_to_repo(self, service, search_repo):
        search_repo.search.return_value = []
        org_id = uuid4()

        await service.search("query", org_id)
        call_args = search_repo.search.call_args[0]
        assert org_id in call_args


class TestSearchForConcept:
    async def test_builds_expanded_query(self, service, search_repo, embedding_client):
        search_repo.search.return_value = [_make_search_row()]

        results = await service.search_for_concept("machine learning", uuid4())

        embed_call = embedding_client.embed.call_args[0][0]
        assert "machine learning" in embed_call
        assert len(results) == 1

    async def test_returns_search_results(self, service, search_repo):
        search_repo.search.return_value = [_make_search_row()]

        results = await service.search_for_concept("python basics", uuid4())
        assert isinstance(results[0], SearchResult)

    async def test_passes_org_id(self, service, search_repo):
        search_repo.search.return_value = []
        org_id = uuid4()

        await service.search_for_concept("concept", org_id)
        call_args = search_repo.search.call_args[0]
        assert org_id in call_args
