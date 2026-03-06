from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from app.domain.document import Document
from app.repositories.document_repository import DocumentRepository
from app.repositories.embedding_client import EmbeddingClient
from app.services.chunker import chunk_text, chunk_code, chunk_markdown, RUST_CHUNKER

if TYPE_CHECKING:
    from app.services.extraction_service import ExtractionService

logger = structlog.get_logger()

_CODE_SOURCE_TYPES = frozenset({"github", "code"})
_MARKDOWN_SOURCE_TYPES = frozenset({"markdown"})

_EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".rs": "rust",
}


class IngestionService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        embedding_client: EmbeddingClient,
        extraction_service: ExtractionService | None = None,
    ) -> None:
        self._repo = document_repo
        self._embedder = embedding_client
        self._extraction = extraction_service

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
            ext = "." + source_path.rsplit(".", 1)[-1] if "." in source_path else ""
            language = _EXT_TO_LANGUAGE.get(ext, "python")
            text_chunks = chunk_code(content, language=language)
        elif source_type in _MARKDOWN_SOURCE_TYPES:
            raw = chunk_markdown(content)
            text_chunks = [c.text if hasattr(c, "text") else c for c in raw]
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

        if self._extraction is not None:
            try:
                await self._extraction.extract_and_store(org_id, doc.id, content)
            except Exception:
                logger.warning("extraction_after_ingestion_failed", document_id=str(doc.id))

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
