import math
from uuid import UUID

from app.repositories.vector_store import VectorPayload, VectorSearchResult, VectorStorePort


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class StubVectorStore(VectorStorePort):
    """In-memory vector store for tests and local development (no Qdrant required)."""

    def __init__(self) -> None:
        # chunk_id -> (embedding, payload)
        self._store: dict[UUID, tuple[list[float], VectorPayload]] = {}

    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        """No-op for the stub — no external collection to create."""

    async def upsert(
        self,
        chunk_id: UUID,
        embedding: list[float],
        payload: VectorPayload,
    ) -> None:
        self._store[chunk_id] = (embedding, payload)

    async def search(
        self,
        embedding: list[float],
        org_id: UUID,
        limit: int,
    ) -> list[VectorSearchResult]:
        scored: list[VectorSearchResult] = []
        for chunk_id, (vec, payload) in self._store.items():
            if payload.org_id != org_id:
                continue
            score = _cosine_similarity(embedding, vec)
            scored.append(VectorSearchResult(chunk_id=chunk_id, score=score))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]

    async def delete(self, chunk_id: UUID) -> None:
        self._store.pop(chunk_id, None)

    async def delete_by_document(self, document_id: UUID) -> None:
        to_remove = [
            cid for cid, (_, payload) in self._store.items()
            if payload.document_id == document_id
        ]
        for cid in to_remove:
            del self._store[cid]
