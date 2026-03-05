from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.document import Document
from app.domain.search import SearchResult
from app.domain.knowledge_base import KBStats


def _make_document(org_id=None, source_type="text"):
    return Document(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        source_type=source_type,
        source_path="/test.md",
        title="Test Doc",
        content="Some content",
        metadata={},
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def document_repo():
    return AsyncMock()


@pytest.fixture
def concept_store():
    return AsyncMock()


@pytest.fixture
def ingestion_service():
    return AsyncMock()


@pytest.fixture
def search_service():
    return AsyncMock()


@pytest.fixture
def service(document_repo, concept_store, ingestion_service, search_service):
    from app.services.knowledge_base_service import KnowledgeBaseService

    return KnowledgeBaseService(
        document_repo=document_repo,
        concept_store=concept_store,
        ingestion_service=ingestion_service,
        search_service=search_service,
    )


class TestGetStats:
    async def test_returns_kb_stats(self, service, document_repo, concept_store):
        org_id = uuid4()
        now = datetime.now(timezone.utc)
        document_repo.count_by_org.return_value = 5
        document_repo.count_chunks_by_org.return_value = 42
        concept_store.count_by_org.return_value = 10
        document_repo.last_updated_by_org.return_value = now

        stats = await service.get_stats(org_id)

        assert isinstance(stats, KBStats)
        assert stats.total_documents == 5
        assert stats.total_chunks == 42
        assert stats.total_concepts == 10
        assert stats.last_updated == now

    async def test_returns_none_last_updated_when_empty(self, service, document_repo, concept_store):
        org_id = uuid4()
        document_repo.count_by_org.return_value = 0
        document_repo.count_chunks_by_org.return_value = 0
        concept_store.count_by_org.return_value = 0
        document_repo.last_updated_by_org.return_value = None

        stats = await service.get_stats(org_id)

        assert stats.total_documents == 0
        assert stats.last_updated is None

    async def test_passes_org_id_to_repos(self, service, document_repo, concept_store):
        org_id = uuid4()
        document_repo.count_by_org.return_value = 0
        document_repo.count_chunks_by_org.return_value = 0
        concept_store.count_by_org.return_value = 0
        document_repo.last_updated_by_org.return_value = None

        await service.get_stats(org_id)

        document_repo.count_by_org.assert_called_once_with(org_id)
        document_repo.count_chunks_by_org.assert_called_once_with(org_id)
        concept_store.count_by_org.assert_called_once_with(org_id)
        document_repo.last_updated_by_org.assert_called_once_with(org_id)


class TestListSources:
    async def test_returns_documents(self, service, document_repo):
        org_id = uuid4()
        docs = [_make_document(org_id), _make_document(org_id)]
        document_repo.get_documents_by_org.return_value = docs

        result = await service.list_sources(org_id)

        assert result == docs
        document_repo.get_documents_by_org.assert_called_once_with(org_id, limit=100, offset=0)

    async def test_returns_empty_list(self, service, document_repo):
        document_repo.get_documents_by_org.return_value = []

        result = await service.list_sources(uuid4())

        assert result == []


class TestSearch:
    async def test_delegates_to_search_service(self, service, search_service):
        org_id = uuid4()
        results = [
            SearchResult(
                chunk_id=uuid4(),
                content="content",
                similarity=0.9,
                document_title="Doc",
                source_type="text",
                source_path="/doc.md",
                metadata={},
            )
        ]
        search_service.search.return_value = results

        got = await service.search(org_id, "what is python?", limit=3)

        search_service.search.assert_called_once_with("what is python?", org_id, limit=3)
        assert got == results

    async def test_default_limit(self, service, search_service):
        search_service.search.return_value = []

        await service.search(uuid4(), "query")

        _, kwargs = search_service.search.call_args
        assert kwargs["limit"] == 5


class TestGetConceptGraph:
    async def test_returns_nodes_and_edges(self, service, concept_store):
        org_id = uuid4()
        c1, c2 = uuid4(), uuid4()
        concept_store.get_org_concepts.return_value = [
            {"id": c1, "organization_id": org_id, "name": "Python", "description": "A language"},
            {"id": c2, "organization_id": org_id, "name": "FastAPI", "description": "A framework"},
        ]
        concept_store.get_relationships_by_org.return_value = [
            {"concept_id": c1, "related_concept_id": c2, "relationship_type": "related"},
        ]

        graph = await service.get_concept_graph(org_id)

        assert len(graph["nodes"]) == 2
        assert graph["nodes"][0] == {"id": str(c1), "name": "Python", "description": "A language"}
        assert len(graph["edges"]) == 1
        assert graph["edges"][0] == {"source": str(c1), "target": str(c2), "type": "related"}

    async def test_empty_graph(self, service, concept_store):
        concept_store.get_org_concepts.return_value = []
        concept_store.get_relationships_by_org.return_value = []

        graph = await service.get_concept_graph(uuid4())

        assert graph == {"nodes": [], "edges": []}

    async def test_passes_org_id(self, service, concept_store):
        org_id = uuid4()
        concept_store.get_org_concepts.return_value = []
        concept_store.get_relationships_by_org.return_value = []

        await service.get_concept_graph(org_id)

        concept_store.get_org_concepts.assert_called_once_with(org_id)
        concept_store.get_relationships_by_org.assert_called_once_with(org_id)


class TestRefreshSource:
    async def test_re_ingests_document(self, service, document_repo, ingestion_service):
        doc = _make_document()
        document_repo.get_document.return_value = doc
        document_repo.delete_chunks_by_document.return_value = None
        ingestion_service.ingest.return_value = doc

        result = await service.refresh_source(doc.id)

        document_repo.get_document.assert_called_once_with(doc.id)
        document_repo.delete_chunks_by_document.assert_called_once_with(doc.id)
        ingestion_service.ingest.assert_called_once_with(
            org_id=doc.organization_id,
            source_type=doc.source_type,
            source_path=doc.source_path,
            title=doc.title,
            content=doc.content,
            metadata=doc.metadata,
        )
        assert result == doc

    async def test_raises_not_found(self, service, document_repo):
        from common.errors import NotFoundError

        document_repo.get_document.return_value = None

        with pytest.raises(NotFoundError):
            await service.refresh_source(uuid4())
