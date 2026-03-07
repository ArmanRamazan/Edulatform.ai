from __future__ import annotations

from uuid import UUID

import structlog

from app.adapters.github_adapter import GitHubAdapter
from app.domain.github_repo import OrgGithubRepo
from app.repositories.github_repo_repository import OrgGithubRepoRepository
from app.services.ingestion_service import IngestionService

logger = structlog.get_logger()

_CONNECT_EXTENSIONS = [".md"]
_WEBHOOK_EXTENSIONS = frozenset({".md", ".py", ".rs", ".ts"})


class GitHubConnectService:
    def __init__(
        self,
        repo_repository: OrgGithubRepoRepository,
        github_adapter: GitHubAdapter,
        ingestion_service: IngestionService,
    ) -> None:
        self._repo_repository = repo_repository
        self._github_adapter = github_adapter
        self._ingestion_service = ingestion_service

    async def connect(
        self,
        org_id: UUID,
        repo_url: str,
        branch: str = "main",
    ) -> tuple[OrgGithubRepo, int]:
        owner, repo_name = self._parse_repo_url(repo_url)
        repo_full = f"{owner}/{repo_name}"

        files = await self._github_adapter.list_files(
            owner=owner,
            repo=repo_name,
            branch=branch,
            extensions=_CONNECT_EXTENSIONS,
        )

        ingested = 0
        for entry in files:
            path = entry["path"]
            try:
                content = await self._github_adapter.get_file_content(
                    owner, repo_name, path, branch
                )
                await self._ingestion_service.ingest(
                    org_id=org_id,
                    source_type="github",
                    source_path=f"{repo_full}/{path}",
                    title=path,
                    content=content,
                    metadata={"repo": repo_full, "branch": branch},
                )
                ingested += 1
            except Exception:
                logger.warning("connect_file_ingest_failed", path=path, repo=repo_full)

        repo_entity = await self._repo_repository.upsert(
            organization_id=org_id,
            repo_url=repo_url,
            branch=branch,
        )
        return repo_entity, ingested

    async def process_webhook(self, payload: dict) -> int:
        full_name = payload.get("repository", {}).get("full_name", "")
        if not full_name:
            return 0

        repo_url = f"https://github.com/{full_name}"
        records = await self._repo_repository.list_by_repo_url(repo_url)
        if not records:
            return 0

        # Extract branch from ref: "refs/heads/feature/x" → "feature/x"
        ref = payload.get("ref", "refs/heads/main")
        parts = ref.split("/", 2)
        branch = parts[2] if len(parts) == 3 else ref

        # Collect added + modified files (skip removed)
        changed: set[str] = set()
        for commit in payload.get("commits", []):
            changed.update(commit.get("added", []))
            changed.update(commit.get("modified", []))

        relevant = [
            path for path in changed
            if any(path.endswith(ext) for ext in _WEBHOOK_EXTENSIONS)
        ]

        if not relevant:
            return 0

        owner, repo_name = full_name.split("/", 1)
        processed = 0

        for record in records:
            for path in relevant:
                try:
                    content = await self._github_adapter.get_file_content(
                        owner, repo_name, path, branch
                    )
                    await self._ingestion_service.ingest(
                        org_id=record.organization_id,
                        source_type="github",
                        source_path=f"{full_name}/{path}",
                        title=path,
                        content=content,
                        metadata={"repo": full_name, "branch": branch},
                    )
                    processed += 1
                except Exception:
                    logger.warning(
                        "webhook_file_ingest_failed",
                        path=path,
                        repo=full_name,
                    )

        return processed

    @staticmethod
    def _parse_repo_url(repo_url: str) -> tuple[str, str]:
        url = repo_url.strip().rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        parts = [p for p in url.split("/") if p]
        if len(parts) < 2:
            from common.errors import AppError
            raise AppError("Invalid GitHub repository URL", status_code=400)
        return parts[-2], parts[-1]
