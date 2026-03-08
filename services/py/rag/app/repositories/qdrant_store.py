import structlog
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    HnswConfigDiff,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from app.repositories.vector_store import VectorPayload, VectorSearchResult, VectorStorePort

logger = structlog.get_logger()


class QdrantStore(VectorStorePort):
    """Qdrant-backed vector store using AsyncQdrantClient."""

    def __init__(self, url: str, collection: str) -> None:
        self._client = AsyncQdrantClient(url=url)
        self._collection = collection

    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        """Create the Qdrant collection if it does not exist. Idempotent."""
        exists = await self._client.collection_exists(collection)
        if not exists:
            await self._client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                    hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
                ),
            )
            logger.info("qdrant_collection_created", collection=collection, vector_size=vector_size)
        else:
            logger.debug("qdrant_collection_exists", collection=collection)

    async def upsert(
        self,
        chunk_id: UUID,
        embedding: list[float],
        payload: VectorPayload,
    ) -> None:
        await self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(
                    id=str(chunk_id),
                    vector=embedding,
                    payload={
                        "chunk_id": str(payload.chunk_id),
                        "document_id": str(payload.document_id),
                        "org_id": str(payload.org_id),
                    },
                )
            ],
        )

    async def search(
        self,
        embedding: list[float],
        org_id: UUID,
        limit: int,
    ) -> list[VectorSearchResult]:
        results = await self._client.search(
            collection_name=self._collection,
            query_vector=embedding,
            limit=limit,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="org_id",
                        match=MatchValue(value=str(org_id)),
                    )
                ]
            ),
            with_payload=False,
        )
        return [
            VectorSearchResult(chunk_id=UUID(hit.id), score=hit.score)
            for hit in results
        ]

    async def delete(self, chunk_id: UUID) -> None:
        await self._client.delete(
            collection_name=self._collection,
            points_selector=PointIdsList(points=[str(chunk_id)]),
        )

    async def delete_by_document(self, document_id: UUID) -> None:
        await self._client.delete(
            collection_name=self._collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )

    async def close(self) -> None:
        await self._client.close()
