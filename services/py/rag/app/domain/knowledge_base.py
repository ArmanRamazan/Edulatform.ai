from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class KBStats:
    total_documents: int
    total_chunks: int
    total_concepts: int
    last_updated: datetime | None
