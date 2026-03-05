from __future__ import annotations

from uuid import UUID

from common.errors import NotFoundError
from app.domain.document import Document
from app.domain.knowledge_base import KBStats
from app.domain.search import SearchResult
from app.repositories.document_repository import DocumentRepository
from app.repositories.concept_store import ConceptStoreRepository
from app.services.ingestion_service import IngestionService
from app.services.search_service import SearchService


class KnowledgeBaseService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        concept_store: ConceptStoreRepository,
        ingestion_service: IngestionService,
        search_service: SearchService,
    ) -> None:
        self._doc_repo = document_repo
        self._concept_store = concept_store
        self._ingestion = ingestion_service
        self._search = search_service

    async def get_stats(self, org_id: UUID) -> KBStats:
        total_documents = await self._doc_repo.count_by_org(org_id)
        total_chunks = await self._doc_repo.count_chunks_by_org(org_id)
        total_concepts = await self._concept_store.count_by_org(org_id)
        last_updated = await self._doc_repo.last_updated_by_org(org_id)
        return KBStats(
            total_documents=total_documents,
            total_chunks=total_chunks,
            total_concepts=total_concepts,
            last_updated=last_updated,
        )

    async def list_sources(self, org_id: UUID) -> list[Document]:
        return await self._doc_repo.get_documents_by_org(org_id, limit=100, offset=0)

    async def search(
        self,
        org_id: UUID,
        query: str,
        limit: int = 5,
    ) -> list[SearchResult]:
        return await self._search.search(query, org_id, limit=limit)

    async def get_concept_graph(self, org_id: UUID) -> dict:
        concepts = await self._concept_store.get_org_concepts(org_id)
        relationships = await self._concept_store.get_relationships_by_org(org_id)

        nodes = [
            {
                "id": str(c["id"]),
                "name": c["name"],
                "description": c["description"],
            }
            for c in concepts
        ]
        edges = [
            {
                "source": str(r["concept_id"]),
                "target": str(r["related_concept_id"]),
                "type": r["relationship_type"],
            }
            for r in relationships
        ]
        return {"nodes": nodes, "edges": edges}

    async def refresh_source(self, document_id: UUID) -> Document:
        doc = await self._doc_repo.get_document(document_id)
        if doc is None:
            raise NotFoundError("Document not found")

        await self._doc_repo.delete_chunks_by_document(document_id)

        return await self._ingestion.ingest(
            org_id=doc.organization_id,
            source_type=doc.source_type,
            source_path=doc.source_path,
            title=doc.title,
            content=doc.content,
            metadata=doc.metadata,
        )
