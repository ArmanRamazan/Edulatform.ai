from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.github_repo import OrgGithubRepo
from app.services.github_connect_service import GitHubConnectService


def _make_repo(org_id=None, repo_url="https://github.com/owner/repo") -> OrgGithubRepo:
    return OrgGithubRepo(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        repo_url=repo_url,
        branch="main",
        last_synced_at=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def repo_repository():
    return AsyncMock()


@pytest.fixture
def github_adapter():
    return AsyncMock()


@pytest.fixture
def ingestion_service():
    return AsyncMock()


@pytest.fixture
def service(repo_repository, github_adapter, ingestion_service):
    return GitHubConnectService(
        repo_repository=repo_repository,
        github_adapter=github_adapter,
        ingestion_service=ingestion_service,
    )


class TestConnect:
    async def test_ingests_md_files_from_repo(
        self, service, github_adapter, ingestion_service, repo_repository
    ):
        org_id = uuid4()
        repo_url = "https://github.com/myorg/myrepo"
        repo_entity = _make_repo(org_id=org_id, repo_url=repo_url)

        github_adapter.list_files.return_value = [
            {"path": "README.md", "type": "blob", "size": 100},
            {"path": "docs/overview.md", "type": "blob", "size": 200},
        ]
        github_adapter.get_file_content.return_value = "# Content"
        repo_repository.upsert.return_value = repo_entity

        result_repo, count = await service.connect(
            org_id=org_id, repo_url=repo_url, branch="main"
        )

        assert count == 2
        assert ingestion_service.ingest.call_count == 2
        assert result_repo == repo_entity

    async def test_connect_uses_md_extension_filter(
        self, service, github_adapter, repo_repository
    ):
        github_adapter.list_files.return_value = []
        repo_repository.upsert.return_value = _make_repo()

        await service.connect(
            org_id=uuid4(), repo_url="https://github.com/o/r", branch="main"
        )

        github_adapter.list_files.assert_called_once()
        call = github_adapter.list_files.call_args
        # Accept positional or keyword
        extensions = call.kwargs.get("extensions") or (
            call.args[3] if len(call.args) > 3 else None
        )
        assert extensions is not None
        assert ".md" in extensions

    async def test_connect_parses_github_url_correctly(
        self, service, github_adapter, repo_repository
    ):
        github_adapter.list_files.return_value = []
        repo_repository.upsert.return_value = _make_repo()

        await service.connect(
            org_id=uuid4(),
            repo_url="https://github.com/myorg/myrepo",
            branch="main",
        )

        call = github_adapter.list_files.call_args
        owner = call.kwargs.get("owner") or call.args[0]
        repo = call.kwargs.get("repo") or call.args[1]
        assert owner == "myorg"
        assert repo == "myrepo"

    async def test_connect_stores_repo_connection(
        self, service, github_adapter, repo_repository
    ):
        org_id = uuid4()
        repo_url = "https://github.com/myorg/myrepo"
        github_adapter.list_files.return_value = []
        repo_repository.upsert.return_value = _make_repo(org_id=org_id, repo_url=repo_url)

        await service.connect(org_id=org_id, repo_url=repo_url, branch="develop")

        repo_repository.upsert.assert_called_once_with(
            organization_id=org_id,
            repo_url=repo_url,
            branch="develop",
        )

    async def test_connect_returns_zero_when_no_md_files(
        self, service, github_adapter, repo_repository
    ):
        github_adapter.list_files.return_value = []
        repo_repository.upsert.return_value = _make_repo()

        _, count = await service.connect(
            org_id=uuid4(), repo_url="https://github.com/o/r"
        )

        assert count == 0

    async def test_connect_ingest_error_does_not_stop_other_files(
        self, service, github_adapter, ingestion_service, repo_repository
    ):
        github_adapter.list_files.return_value = [
            {"path": "README.md", "size": 100},
            {"path": "docs/guide.md", "size": 200},
        ]
        github_adapter.get_file_content.return_value = "content"
        ingestion_service.ingest.side_effect = [Exception("db error"), None]
        repo_repository.upsert.return_value = _make_repo()

        _, count = await service.connect(
            org_id=uuid4(), repo_url="https://github.com/o/r"
        )

        # Both files attempted
        assert ingestion_service.ingest.call_count == 2
        # Only the second succeeded
        assert count == 1

    async def test_connect_ingest_passes_correct_metadata(
        self, service, github_adapter, ingestion_service, repo_repository
    ):
        org_id = uuid4()
        github_adapter.list_files.return_value = [
            {"path": "README.md", "size": 100},
        ]
        github_adapter.get_file_content.return_value = "# Hello"
        repo_repository.upsert.return_value = _make_repo(org_id=org_id)

        await service.connect(
            org_id=org_id, repo_url="https://github.com/myorg/myrepo", branch="main"
        )

        call_kwargs = ingestion_service.ingest.call_args.kwargs
        assert call_kwargs["org_id"] == org_id
        assert call_kwargs["source_type"] == "github"
        assert "myorg/myrepo" in call_kwargs["source_path"]
        assert call_kwargs["metadata"]["branch"] == "main"

    async def test_connect_strips_git_suffix_from_url(
        self, service, github_adapter, repo_repository
    ):
        github_adapter.list_files.return_value = []
        repo_repository.upsert.return_value = _make_repo()

        await service.connect(
            org_id=uuid4(),
            repo_url="https://github.com/myorg/myrepo.git",
            branch="main",
        )

        call = github_adapter.list_files.call_args
        owner = call.kwargs.get("owner") or call.args[0]
        repo = call.kwargs.get("repo") or call.args[1]
        assert owner == "myorg"
        assert repo == "myrepo"


class TestProcessWebhook:
    async def test_processes_push_event_changed_files(
        self, service, github_adapter, ingestion_service, repo_repository
    ):
        org_id = uuid4()
        repo_record = _make_repo(org_id=org_id, repo_url="https://github.com/owner/repo")
        repo_repository.list_by_repo_url.return_value = [repo_record]
        github_adapter.get_file_content.return_value = "# Updated content"

        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "owner/repo"},
            "commits": [
                {"added": ["docs/new.md"], "modified": ["README.md"], "removed": []}
            ],
        }

        count = await service.process_webhook(payload)

        assert count == 2
        assert ingestion_service.ingest.call_count == 2

    async def test_webhook_returns_zero_for_unknown_repo(
        self, service, repo_repository
    ):
        repo_repository.list_by_repo_url.return_value = []

        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "unknown/repo"},
            "commits": [{"added": ["README.md"], "modified": [], "removed": []}],
        }

        count = await service.process_webhook(payload)
        assert count == 0

    async def test_webhook_filters_by_supported_extensions(
        self, service, github_adapter, ingestion_service, repo_repository
    ):
        repo_record = _make_repo()
        repo_repository.list_by_repo_url.return_value = [repo_record]
        github_adapter.get_file_content.return_value = "content"

        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "owner/repo"},
            "commits": [
                {
                    "added": [
                        "README.md",
                        "src/main.py",
                        "lib/utils.rs",
                        "app/index.ts",
                        "image.png",
                        "style.css",
                    ],
                    "modified": [],
                    "removed": [],
                }
            ],
        }

        count = await service.process_webhook(payload)

        # .md, .py, .rs, .ts — 4 files; .png, .css — excluded
        assert count == 4

    async def test_webhook_skips_removed_files(
        self, service, github_adapter, ingestion_service, repo_repository
    ):
        repo_record = _make_repo()
        repo_repository.list_by_repo_url.return_value = [repo_record]
        github_adapter.get_file_content.return_value = "content"

        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "owner/repo"},
            "commits": [
                {
                    "added": [],
                    "modified": ["README.md"],
                    "removed": ["old.md"],
                }
            ],
        }

        count = await service.process_webhook(payload)
        assert count == 1  # Only modified, not removed

    async def test_webhook_handles_file_fetch_error_gracefully(
        self, service, github_adapter, ingestion_service, repo_repository
    ):
        repo_record = _make_repo()
        repo_repository.list_by_repo_url.return_value = [repo_record]
        github_adapter.get_file_content.side_effect = [Exception("404"), "content"]

        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "owner/repo"},
            "commits": [
                {"added": ["missing.md", "README.md"], "modified": [], "removed": []}
            ],
        }

        count = await service.process_webhook(payload)
        # First fetch fails, second succeeds
        assert count == 1

    async def test_webhook_processes_for_all_connected_orgs(
        self, service, github_adapter, ingestion_service, repo_repository
    ):
        org_a = uuid4()
        org_b = uuid4()
        records = [
            _make_repo(org_id=org_a, repo_url="https://github.com/owner/repo"),
            _make_repo(org_id=org_b, repo_url="https://github.com/owner/repo"),
        ]
        repo_repository.list_by_repo_url.return_value = records
        github_adapter.get_file_content.return_value = "content"

        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "owner/repo"},
            "commits": [{"added": ["README.md"], "modified": [], "removed": []}],
        }

        count = await service.process_webhook(payload)

        # 1 file × 2 orgs = 2 ingestions
        assert count == 2
        assert ingestion_service.ingest.call_count == 2

    async def test_webhook_extracts_branch_from_ref(
        self, service, github_adapter, ingestion_service, repo_repository
    ):
        repo_record = _make_repo()
        repo_repository.list_by_repo_url.return_value = [repo_record]
        github_adapter.get_file_content.return_value = "content"

        payload = {
            "ref": "refs/heads/feature/my-branch",
            "repository": {"full_name": "owner/repo"},
            "commits": [{"added": ["README.md"], "modified": [], "removed": []}],
        }

        await service.process_webhook(payload)

        call_kwargs = ingestion_service.ingest.call_args.kwargs
        assert call_kwargs["metadata"]["branch"] == "feature/my-branch"

    async def test_webhook_returns_zero_when_no_changed_files(
        self, service, repo_repository
    ):
        repo_record = _make_repo()
        repo_repository.list_by_repo_url.return_value = [repo_record]

        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "owner/repo"},
            "commits": [{"added": [], "modified": [], "removed": ["deleted.md"]}],
        }

        count = await service.process_webhook(payload)
        assert count == 0
