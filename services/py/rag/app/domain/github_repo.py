from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class OrgGithubRepo:
    id: UUID
    organization_id: UUID
    repo_url: str
    branch: str
    last_synced_at: datetime | None
    created_at: datetime
