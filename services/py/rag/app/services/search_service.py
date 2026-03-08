from __future__ import annotations

from uuid import UUID

from app.domain.search import SearchResult
from app.repositories.vector_store import VectorStorePort
from app.repositories.document_repository import DocumentRepository
from app.repositories.embedding_client import EmbeddingClient


class SearchService:
    def __init__(
        self,
        vector_store: VectorStorePort,
        document_repo: DocumentRepository,
        embedding_client: EmbeddingClient,
    ) -> None:
        self._vector_store = vector_store
        self._doc_repo = document_repo
        self._embedding_client = embedding_client

    async def search(
        self,
        query: str,
        org_id: UUID,
        limit: int = 5,
    ) -> list[SearchResult]:
        embedding = await self._embedding_client.embed(query)
        vector_results = await self._vector_store.search(embedding, org_id, limit=limit)
        if not vector_results:
            return []

        chunk_ids = [r.chunk_id for r in vector_results]
        score_map = {r.chunk_id: r.score for r in vector_results}
        rows = await self._doc_repo.get_chunks_with_documents(chunk_ids)

        results: list[SearchResult] = []
        for row in rows:
            cid = row["id"]
            if cid in score_map:
                results.append(SearchResult(
                    chunk_id=cid,
                    content=row["content"],
                    similarity=score_map[cid],
                    document_title=row["document_title"],
                    source_type=row["source_type"],
                    source_path=row["source_path"],
                    metadata=row["metadata"],
                ))
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results

    async def search_for_concept(
        self,
        concept_name: str,
        org_id: UUID,
    ) -> list[SearchResult]:
        expanded_query = f"{concept_name} definition explanation examples"
        return await self.search(expanded_query, org_id)
