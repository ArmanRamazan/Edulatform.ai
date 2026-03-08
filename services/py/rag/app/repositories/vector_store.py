from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class VectorPayload:
    """Metadata stored alongside each embedding vector."""

    chunk_id: UUID
    document_id: UUID
    org_id: UUID


@dataclass(frozen=True)
class VectorSearchResult:
    """Single result from a vector similarity search."""

    chunk_id: UUID
    score: float  # cosine similarity, 0.0–1.0


class VectorStorePort(ABC):
    """Abstract port for vector embedding storage and similarity search."""

    @abstractmethod
    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        """Create collection if it does not exist. Idempotent."""
        ...

    @abstractmethod
    async def upsert(
        self,
        chunk_id: UUID,
        embedding: list[float],
        payload: VectorPayload,
    ) -> None:
        """Insert or update a single embedding with its payload."""
        ...

    @abstractmethod
    async def search(
        self,
        embedding: list[float],
        org_id: UUID,
        limit: int,
    ) -> list[VectorSearchResult]:
        """Return top-k results filtered by org_id, ordered by similarity desc."""
        ...

    @abstractmethod
    async def delete(self, chunk_id: UUID) -> None:
        """Remove a single embedding by chunk ID. No-op if not found."""
        ...

    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> None:
        """Remove all embeddings belonging to a document. No-op if none found."""
        ...
