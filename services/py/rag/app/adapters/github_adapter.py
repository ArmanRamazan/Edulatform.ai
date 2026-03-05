from __future__ import annotations

import asyncio
import base64
from uuid import UUID

import httpx
import structlog

from app.services.ingestion_service import IngestionService

logger = structlog.get_logger()

_MAX_FILE_SIZE = 100_000  # 100KB
_BATCH_SIZE = 10
_BATCH_DELAY = 0.1  # seconds between batches
_DEFAULT_EXTENSIONS = [".py", ".ts", ".md", ".yaml"]
_GITHUB_API = "https://api.github.com"


class GitHubAdapter:
    def __init__(self, http_client: httpx.AsyncClient, github_token: str = "") -> None:
        self._http = http_client
        self._token = github_token

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        if self._token:
            headers["Authorization"] = f"token {self._token}"
        return headers

    async def list_files(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        extensions: list[str] | None = None,
    ) -> list[dict]:
        if extensions is None:
            extensions = _DEFAULT_EXTENSIONS

        url = f"{_GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}"
        resp = await self._http.get(
            url,
            params={"recursive": "1"},
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json()

        files = []
        for entry in data.get("tree", []):
            if entry.get("type") != "blob":
                continue
            path = entry["path"]
            size = entry.get("size", 0)
            if size > _MAX_FILE_SIZE:
                continue
            if not any(path.endswith(ext) for ext in extensions):
                continue
            files.append(entry)
        return files

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: str = "main",
    ) -> str:
        url = f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
        resp = await self._http.get(
            url,
            params={"ref": branch},
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        content_b64 = data["content"]
        return base64.b64decode(content_b64).decode()

    async def index_repository(
        self,
        org_id: UUID,
        owner: str,
        repo: str,
        branch: str,
        extensions: list[str],
        ingestion_service: IngestionService,
    ) -> int:
        files = await self.list_files(owner, repo, branch, extensions)
        indexed = 0
        repo_full = f"{owner}/{repo}"

        for batch_start in range(0, len(files), _BATCH_SIZE):
            if batch_start > 0:
                await asyncio.sleep(_BATCH_DELAY)

            batch = files[batch_start : batch_start + _BATCH_SIZE]
            for entry in batch:
                path = entry["path"]
                try:
                    content = await self.get_file_content(owner, repo, path, branch)
                except Exception:
                    logger.warning("github_file_fetch_failed", path=path, repo=repo_full)
                    continue

                try:
                    await ingestion_service.ingest(
                        org_id=org_id,
                        source_type="github",
                        source_path=f"{repo_full}/{path}",
                        title=path,
                        content=content,
                        metadata={"repo": repo_full, "branch": branch},
                    )
                    indexed += 1
                except Exception:
                    logger.warning("github_file_ingest_failed", path=path, repo=repo_full)

        return indexed
