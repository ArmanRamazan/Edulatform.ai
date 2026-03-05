from __future__ import annotations

import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.adapters.github_adapter import GitHubAdapter


def _tree_response(files: list[dict]) -> dict:
    return {
        "sha": "abc123",
        "tree": files,
        "truncated": False,
    }


def _make_tree_entry(path: str, size: int = 500) -> dict:
    return {"path": path, "type": "blob", "size": size}


def _content_response(text: str) -> dict:
    encoded = base64.b64encode(text.encode()).decode()
    return {"content": encoded, "encoding": "base64"}


class TestListFiles:
    @pytest.fixture
    def mock_http(self) -> AsyncMock:
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def adapter(self, mock_http: AsyncMock) -> GitHubAdapter:
        return GitHubAdapter(http_client=mock_http, github_token="test-token")

    async def test_returns_filtered_files(self, adapter, mock_http):
        tree = _tree_response([
            _make_tree_entry("src/main.py", 200),
            _make_tree_entry("src/utils.ts", 300),
            _make_tree_entry("README.md", 100),
            _make_tree_entry("image.png", 500),
            _make_tree_entry("data.json", 400),
        ])
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = tree
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        files = await adapter.list_files("owner", "repo", extensions=[".py", ".ts", ".md"])
        assert len(files) == 3
        paths = [f["path"] for f in files]
        assert "src/main.py" in paths
        assert "src/utils.ts" in paths
        assert "README.md" in paths
        assert "image.png" not in paths

    async def test_skips_files_over_100kb(self, adapter, mock_http):
        tree = _tree_response([
            _make_tree_entry("small.py", 1000),
            _make_tree_entry("large.py", 200_000),
        ])
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = tree
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        files = await adapter.list_files("owner", "repo", extensions=[".py"])
        assert len(files) == 1
        assert files[0]["path"] == "small.py"

    async def test_skips_non_blob_entries(self, adapter, mock_http):
        tree = _tree_response([
            {"path": "src", "type": "tree", "size": 0},
            _make_tree_entry("src/main.py", 200),
        ])
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = tree
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        files = await adapter.list_files("owner", "repo", extensions=[".py"])
        assert len(files) == 1
        assert files[0]["path"] == "src/main.py"

    async def test_uses_correct_url_and_headers(self, adapter, mock_http):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _tree_response([])
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        await adapter.list_files("myowner", "myrepo", branch="develop")
        mock_http.get.assert_called_once_with(
            "https://api.github.com/repos/myowner/myrepo/git/trees/develop",
            params={"recursive": "1"},
            headers={"Authorization": "token test-token", "Accept": "application/vnd.github.v3+json"},
        )

    async def test_no_token_omits_auth_header(self, mock_http):
        adapter = GitHubAdapter(http_client=mock_http, github_token="")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _tree_response([])
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        await adapter.list_files("owner", "repo")
        call_kwargs = mock_http.get.call_args
        assert "Authorization" not in call_kwargs.kwargs.get("headers", {})

    async def test_default_extensions(self, adapter, mock_http):
        tree = _tree_response([
            _make_tree_entry("main.py", 100),
            _make_tree_entry("app.ts", 100),
            _make_tree_entry("readme.md", 100),
            _make_tree_entry("config.yaml", 100),
            _make_tree_entry("style.css", 100),
        ])
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = tree
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        files = await adapter.list_files("owner", "repo")
        assert len(files) == 4
        paths = [f["path"] for f in files]
        assert "style.css" not in paths


class TestGetFileContent:
    @pytest.fixture
    def mock_http(self) -> AsyncMock:
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def adapter(self, mock_http: AsyncMock) -> GitHubAdapter:
        return GitHubAdapter(http_client=mock_http, github_token="ghp_test")

    async def test_decodes_base64_content(self, adapter, mock_http):
        content_text = "def hello():\n    print('world')"
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _content_response(content_text)
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        result = await adapter.get_file_content("owner", "repo", "src/main.py")
        assert result == content_text

    async def test_uses_correct_url(self, adapter, mock_http):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _content_response("x")
        resp.raise_for_status = MagicMock()
        mock_http.get.return_value = resp

        await adapter.get_file_content("owner", "repo", "src/app.py", branch="dev")
        call_args = mock_http.get.call_args
        assert call_args.args[0] == "https://api.github.com/repos/owner/repo/contents/src/app.py"
        assert call_args.kwargs["params"]["ref"] == "dev"


class TestIndexRepository:
    @pytest.fixture
    def mock_http(self) -> AsyncMock:
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def adapter(self, mock_http: AsyncMock) -> GitHubAdapter:
        return GitHubAdapter(http_client=mock_http, github_token="tok")

    @pytest.fixture
    def ingestion_service(self) -> AsyncMock:
        return AsyncMock()

    async def test_indexes_all_files(self, adapter, mock_http, ingestion_service):
        tree = _tree_response([
            _make_tree_entry("a.py", 100),
            _make_tree_entry("b.py", 200),
        ])
        tree_resp = MagicMock()
        tree_resp.status_code = 200
        tree_resp.json.return_value = tree
        tree_resp.raise_for_status = MagicMock()

        content_resp = MagicMock()
        content_resp.status_code = 200
        content_resp.json.return_value = _content_response("code here")
        content_resp.raise_for_status = MagicMock()

        mock_http.get.side_effect = [tree_resp, content_resp, content_resp]

        org_id = uuid4()
        count = await adapter.index_repository(
            org_id=org_id,
            owner="owner",
            repo="repo",
            branch="main",
            extensions=[".py"],
            ingestion_service=ingestion_service,
        )
        assert count == 2
        assert ingestion_service.ingest.call_count == 2

    async def test_error_on_single_file_does_not_stop_batch(self, adapter, mock_http, ingestion_service):
        tree = _tree_response([
            _make_tree_entry("a.py", 100),
            _make_tree_entry("b.py", 200),
            _make_tree_entry("c.py", 300),
        ])
        tree_resp = MagicMock()
        tree_resp.status_code = 200
        tree_resp.json.return_value = tree
        tree_resp.raise_for_status = MagicMock()

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = _content_response("code")
        ok_resp.raise_for_status = MagicMock()

        fail_resp = MagicMock()
        fail_resp.status_code = 404
        fail_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=fail_resp
        )

        mock_http.get.side_effect = [tree_resp, ok_resp, fail_resp, ok_resp]

        org_id = uuid4()
        count = await adapter.index_repository(
            org_id=org_id,
            owner="owner",
            repo="repo",
            branch="main",
            extensions=[".py"],
            ingestion_service=ingestion_service,
        )
        assert count == 2
        assert ingestion_service.ingest.call_count == 2

    async def test_ingestion_error_does_not_stop_batch(self, adapter, mock_http, ingestion_service):
        tree = _tree_response([
            _make_tree_entry("a.py", 100),
            _make_tree_entry("b.py", 200),
        ])
        tree_resp = MagicMock()
        tree_resp.status_code = 200
        tree_resp.json.return_value = tree
        tree_resp.raise_for_status = MagicMock()

        content_resp = MagicMock()
        content_resp.status_code = 200
        content_resp.json.return_value = _content_response("code")
        content_resp.raise_for_status = MagicMock()

        mock_http.get.side_effect = [tree_resp, content_resp, content_resp]
        ingestion_service.ingest.side_effect = [Exception("db error"), AsyncMock()]

        org_id = uuid4()
        count = await adapter.index_repository(
            org_id=org_id,
            owner="owner",
            repo="repo",
            branch="main",
            extensions=[".py"],
            ingestion_service=ingestion_service,
        )
        assert count == 1

    async def test_passes_correct_source_type_and_metadata(self, adapter, mock_http, ingestion_service):
        tree = _tree_response([_make_tree_entry("src/app.py", 100)])
        tree_resp = MagicMock()
        tree_resp.status_code = 200
        tree_resp.json.return_value = tree
        tree_resp.raise_for_status = MagicMock()

        content_resp = MagicMock()
        content_resp.status_code = 200
        content_resp.json.return_value = _content_response("print('hi')")
        content_resp.raise_for_status = MagicMock()

        mock_http.get.side_effect = [tree_resp, content_resp]

        org_id = uuid4()
        await adapter.index_repository(
            org_id=org_id,
            owner="owner",
            repo="myrepo",
            branch="main",
            extensions=[".py"],
            ingestion_service=ingestion_service,
        )

        call_kwargs = ingestion_service.ingest.call_args.kwargs
        assert call_kwargs["org_id"] == org_id
        assert call_kwargs["source_type"] == "github"
        assert call_kwargs["source_path"] == "owner/myrepo/src/app.py"
        assert call_kwargs["title"] == "src/app.py"
        assert call_kwargs["content"] == "print('hi')"
        assert call_kwargs["metadata"]["repo"] == "owner/myrepo"
        assert call_kwargs["metadata"]["branch"] == "main"

    @patch("app.adapters.github_adapter.asyncio.sleep", new_callable=AsyncMock)
    async def test_batches_with_sleep(self, mock_sleep, mock_http, ingestion_service):
        adapter = GitHubAdapter(http_client=mock_http, github_token="tok")
        entries = [_make_tree_entry(f"file{i}.py", 100) for i in range(15)]
        tree = _tree_response(entries)
        tree_resp = MagicMock()
        tree_resp.status_code = 200
        tree_resp.json.return_value = tree
        tree_resp.raise_for_status = MagicMock()

        content_resp = MagicMock()
        content_resp.status_code = 200
        content_resp.json.return_value = _content_response("code")
        content_resp.raise_for_status = MagicMock()

        mock_http.get.side_effect = [tree_resp] + [content_resp] * 15

        await adapter.index_repository(
            org_id=uuid4(),
            owner="o",
            repo="r",
            branch="main",
            extensions=[".py"],
            ingestion_service=ingestion_service,
        )
        # 15 files / 10 per batch = 2 batches, sleep between batches (1 time)
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_with(0.1)
