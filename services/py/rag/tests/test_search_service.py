from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.search_service import SearchService
from app.domain.search import SearchResult
from app.repositories.vector_store import VectorSearchResult


@pytest.fixture
def vector_store():
    return AsyncMock()


@pytest.fixture
def doc_repo():
    return AsyncMock()


@pytest.fixture
def embedding_client():
    client = AsyncMock()
    client.embed.return_value = [0.1, 0.2, 0.3]
    return client


@pytest.fixture
def service(vector_store, doc_repo, embedding_client):
    return SearchService(
        vector_store=vector_store,
        document_repo=doc_repo,
        embedding_client=embedding_client,
    )


def _make_chunk_row(chunk_id=None):
    return {
        "id": chunk_id or uuid4(),
        "content": "Some relevant content.",
        "document_title": "Test Doc",
        "source_type": "text",
        "source_path": "/doc.md",
        "metadata": {},
        "chunk_index": 0,
    }


class TestSearch:
    async def test_embeds_query_and_searches(self, service, vector_store, doc_repo, embedding_client):
        chunk_id = uuid4()
        vector_store.search.return_value = [VectorSearchResult(chunk_id=chunk_id, score=0.92)]
        doc_repo.get_chunks_with_documents.return_value = [_make_chunk_row(chunk_id=chunk_id)]

        results = await service.search("what is python?", uuid4(), limit=5)

        embedding_client.embed.assert_called_once_with("what is python?")
        vector_store.search.assert_called_once()
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)

    async def test_returns_search_results_with_correct_fields(self, service, vector_store, doc_repo):
        chunk_id = uuid4()
        vector_store.search.return_value = [VectorSearchResult(chunk_id=chunk_id, score=0.92)]
        doc_repo.get_chunks_with_documents.return_value = [_make_chunk_row(chunk_id=chunk_id)]

        results = await service.search("query", uuid4())
        result = results[0]
        assert result.chunk_id == chunk_id
        assert result.content == "Some relevant content."
        assert result.similarity == 0.92
        assert result.document_title == "Test Doc"
        assert result.source_type == "text"
        assert result.source_path == "/doc.md"

    async def test_passes_limit_to_vector_store(self, service, vector_store, doc_repo):
        vector_store.search.return_value = []

        await service.search("query", uuid4(), limit=10)
        call_kwargs = vector_store.search.call_args
        assert call_kwargs[1].get("limit") == 10 or call_kwargs[0][2] == 10

    async def test_empty_results_from_vector_store(self, service, vector_store, doc_repo):
        vector_store.search.return_value = []

        results = await service.search("query", uuid4())
        assert results == []
        doc_repo.get_chunks_with_documents.assert_not_called()

    async def test_passes_org_id_to_vector_store(self, service, vector_store, doc_repo):
        vector_store.search.return_value = []
        org_id = uuid4()

        await service.search("query", org_id)
        call_args = vector_store.search.call_args[0]
        assert org_id in call_args

    async def test_results_sorted_by_similarity_desc(self, service, vector_store, doc_repo):
        id1, id2 = uuid4(), uuid4()
        vector_store.search.return_value = [
            VectorSearchResult(chunk_id=id1, score=0.7),
            VectorSearchResult(chunk_id=id2, score=0.95),
        ]
        doc_repo.get_chunks_with_documents.return_value = [
            _make_chunk_row(chunk_id=id1),
            _make_chunk_row(chunk_id=id2),
        ]

        results = await service.search("query", uuid4())
        assert results[0].similarity > results[1].similarity


class TestSearchForConcept:
    async def test_builds_expanded_query(self, service, vector_store, doc_repo, embedding_client):
        chunk_id = uuid4()
        vector_store.search.return_value = [VectorSearchResult(chunk_id=chunk_id, score=0.9)]
        doc_repo.get_chunks_with_documents.return_value = [_make_chunk_row(chunk_id=chunk_id)]

        results = await service.search_for_concept("machine learning", uuid4())

        embed_call = embedding_client.embed.call_args[0][0]
        assert "machine learning" in embed_call
        assert len(results) == 1

    async def test_returns_search_results(self, service, vector_store, doc_repo):
        chunk_id = uuid4()
        vector_store.search.return_value = [VectorSearchResult(chunk_id=chunk_id, score=0.85)]
        doc_repo.get_chunks_with_documents.return_value = [_make_chunk_row(chunk_id=chunk_id)]

        results = await service.search_for_concept("python basics", uuid4())
        assert isinstance(results[0], SearchResult)

    async def test_passes_org_id(self, service, vector_store, doc_repo):
        vector_store.search.return_value = []
        org_id = uuid4()

        await service.search_for_concept("concept", org_id)
        call_args = vector_store.search.call_args[0]
        assert org_id in call_args
