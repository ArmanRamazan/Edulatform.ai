from __future__ import annotations

from uuid import UUID

from app.domain.search import SearchResult
from app.repositories.search_repository import SearchRepository
from app.repositories.embedding_client import EmbeddingClient


class SearchService:
    def __init__(
        self,
        search_repo: SearchRepository,
        embedding_client: EmbeddingClient,
    ) -> None:
        self._search_repo = search_repo
        self._embedding_client = embedding_client

    async def search(
        self,
        query: str,
        org_id: UUID,
        limit: int = 5,
    ) -> list[SearchResult]:
        embedding = await self._embedding_client.embed(query)
        rows = await self._search_repo.search(embedding, org_id, limit=limit)
        return [self._row_to_result(row) for row in rows]

    async def search_for_concept(
        self,
        concept_name: str,
        org_id: UUID,
    ) -> list[SearchResult]:
        expanded_query = f"{concept_name} definition explanation examples"
        return await self.search(expanded_query, org_id)

    @staticmethod
    def _row_to_result(row: dict) -> SearchResult:
        return SearchResult(
            chunk_id=row["id"],
            content=row["content"],
            similarity=row["similarity"],
            document_title=row["document_title"],
            source_type=row["source_type"],
            source_path=row["source_path"],
            metadata=row["metadata"],
        )
