from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ExtractedConcept:
    name: str
    description: str
    related_concepts: list[str]
    source_document_id: UUID
