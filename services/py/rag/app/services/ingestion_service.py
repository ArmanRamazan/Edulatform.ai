from __future__ import annotations

from uuid import UUID

from app.domain.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.embedding_client import EmbeddingClient
from app.services.chunker import chunk_text, chunk_code


_CODE_SOURCE_TYPES = frozenset({"github", "code"})


class IngestionService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        embedding_client: EmbeddingClient,
    ) -> None:
        self._repo = document_repo
        self._embedder = embedding_client

    async def ingest(
        self,
        org_id: UUID,
        source_type: str,
        source_path: str,
        title: str,
        content: str,
        metadata: dict | None = None,
    ) -> Document:
        metadata = metadata or {}

        doc = await self._repo.create_document(
            org_id=org_id,
            source_type=source_type,
            source_path=source_path,
            title=title,
            content=content,
            metadata=metadata,
        )

        if source_type in _CODE_SOURCE_TYPES:
            text_chunks = chunk_code(content)
        else:
            text_chunks = chunk_text(content)

        if not text_chunks:
            return doc

        embeddings = await self._embedder.embed_batch(text_chunks)

        chunks_data = [
            {
                "content": text,
                "chunk_index": i,
                "embedding": emb,
                "metadata": {},
            }
            for i, (text, emb) in enumerate(zip(text_chunks, embeddings))
        ]

        await self._repo.create_chunks(doc.id, chunks_data)
        return doc

    async def get_documents_by_org(
        self,
        org_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Document]:
        return await self._repo.get_documents_by_org(org_id, limit, offset)

    async def delete(self, document_id: UUID) -> bool:
        return await self._repo.delete_document(document_id)
