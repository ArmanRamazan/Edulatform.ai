from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SearchResult:
    chunk_id: UUID
    content: str
    similarity: float
    document_title: str
    source_type: str
    source_path: str
    metadata: dict
