from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Document:
    id: UUID
    organization_id: UUID
    source_type: str
    source_path: str
    title: str
    content: str
    metadata: dict
    created_at: datetime


@dataclass(frozen=True)
class Chunk:
    id: UUID
    document_id: UUID
    content: str
    chunk_index: int
    metadata: dict
