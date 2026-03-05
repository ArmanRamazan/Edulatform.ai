from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.mission import Mission
from app.repositories.mission_repo import MissionRepository


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def concept_id():
    return uuid4()


@pytest.fixture
def mission_id():
    return uuid4()


def _make_row(
    mission_id,
    user_id,
    org_id,
    concept_id=None,
    mission_type="daily",
    status="pending",
    blueprint=None,
    score=None,
    mastery_delta=None,
    started_at=None,
    completed_at=None,
) -> dict:
    now = datetime.now(timezone.utc)
    data = {
        "id": mission_id,
        "user_id": user_id,
        "organization_id": org_id,
        "concept_id": concept_id,
        "mission_type": mission_type,
        "status": status,
        "blueprint": json.dumps(blueprint or {}),
        "score": score,
        "mastery_delta": mastery_delta,
        "started_at": started_at,
        "completed_at": completed_at,
        "created_at": now,
    }
    return data


def _make_mock_row(data: dict) -> MagicMock:
    """Create a mock that behaves like asyncpg.Record (supports [] access)."""
    mock = MagicMock()
    mock.__getitem__ = lambda self, key: data[key]
    mock.__contains__ = lambda self, key: key in data
    return mock


@pytest.fixture
def mock_pool():
    return AsyncMock()


@pytest.fixture
def repo(mock_pool):
    return MissionRepository(mock_pool)


class TestCreate:
    async def test_create_inserts_and_returns_mission(
        self, repo, mock_pool, user_id, org_id, concept_id, mission_id,
    ):
        blueprint = {"recap": [{"q": "What is X?"}]}
        row_data = _make_row(
            mission_id, user_id, org_id, concept_id,
            blueprint=blueprint,
        )
        mock_pool.fetchrow.return_value = _make_mock_row(row_data)

        result = await repo.create(
            user_id=user_id,
            organization_id=org_id,
            concept_id=concept_id,
            mission_type="daily",
            blueprint=blueprint,
        )

        assert isinstance(result, Mission)
        assert result.id == mission_id
        assert result.user_id == user_id
        assert result.organization_id == org_id
        assert result.concept_id == concept_id
        assert result.mission_type == "daily"
        assert result.status == "pending"
        assert result.blueprint == blueprint

        # Verify parameterized SQL
        call_args = mock_pool.fetchrow.call_args
        sql = call_args[0][0]
        assert "$1" in sql
        assert "$2" in sql
        assert "INSERT INTO missions" in sql

    async def test_create_without_concept_id(
        self, repo, mock_pool, user_id, org_id, mission_id,
    ):
        row_data = _make_row(mission_id, user_id, org_id, mission_type="review")
        mock_pool.fetchrow.return_value = _make_mock_row(row_data)

        result = await repo.create(
            user_id=user_id,
            organization_id=org_id,
            concept_id=None,
            mission_type="review",
            blueprint={},
        )

        assert result.concept_id is None
        assert result.mission_type == "review"


class TestGetById:
    async def test_returns_mission_when_found(
        self, repo, mock_pool, user_id, org_id, mission_id,
    ):
        row_data = _make_row(mission_id, user_id, org_id)
        mock_pool.fetchrow.return_value = _make_mock_row(row_data)

        result = await repo.get_by_id(mission_id)

        assert result is not None
        assert result.id == mission_id
        call_args = mock_pool.fetchrow.call_args
        sql = call_args[0][0]
        assert "$1" in sql
        assert "WHERE id = $1" in sql

    async def test_returns_none_when_not_found(
        self, repo, mock_pool, mission_id,
    ):
        mock_pool.fetchrow.return_value = None

        result = await repo.get_by_id(mission_id)

        assert result is None


class TestGetByUser:
    async def test_returns_list_of_missions(
        self, repo, mock_pool, user_id, org_id,
    ):
        rows = [
            _make_mock_row(_make_row(uuid4(), user_id, org_id)),
            _make_mock_row(_make_row(uuid4(), user_id, org_id)),
        ]
        mock_pool.fetch.return_value = rows

        result = await repo.get_by_user(user_id, limit=20, offset=0)

        assert len(result) == 2
        assert all(isinstance(m, Mission) for m in result)
        call_args = mock_pool.fetch.call_args
        sql = call_args[0][0]
        assert "$1" in sql
        assert "LIMIT" in sql
        assert "OFFSET" in sql

    async def test_returns_empty_list(
        self, repo, mock_pool, user_id,
    ):
        mock_pool.fetch.return_value = []

        result = await repo.get_by_user(user_id)

        assert result == []


class TestGetToday:
    async def test_returns_todays_mission(
        self, repo, mock_pool, user_id, org_id, mission_id,
    ):
        row_data = _make_row(mission_id, user_id, org_id, status="in_progress")
        mock_pool.fetchrow.return_value = _make_mock_row(row_data)

        result = await repo.get_today(user_id)

        assert result is not None
        assert result.id == mission_id
        call_args = mock_pool.fetchrow.call_args
        sql = call_args[0][0]
        assert "$1" in sql
        assert "CURRENT_DATE" in sql
        assert "skipped" in sql

    async def test_returns_none_when_no_mission_today(
        self, repo, mock_pool, user_id,
    ):
        mock_pool.fetchrow.return_value = None

        result = await repo.get_today(user_id)

        assert result is None


class TestUpdateStatus:
    async def test_updates_status_with_score(
        self, repo, mock_pool, user_id, org_id, mission_id,
    ):
        now = datetime.now(timezone.utc)
        row_data = _make_row(
            mission_id, user_id, org_id,
            status="completed",
            score=0.85,
            mastery_delta=0.15,
            completed_at=now,
        )
        mock_pool.fetchrow.return_value = _make_mock_row(row_data)

        result = await repo.update_status(
            mission_id=mission_id,
            status="completed",
            score=0.85,
            mastery_delta=0.15,
            completed_at=now,
        )

        assert result.status == "completed"
        assert result.score == 0.85
        assert result.mastery_delta == 0.15
        assert result.completed_at == now
        call_args = mock_pool.fetchrow.call_args
        sql = call_args[0][0]
        assert "UPDATE missions" in sql
        assert "$1" in sql

    async def test_updates_to_in_progress_with_started_at(
        self, repo, mock_pool, user_id, org_id, mission_id,
    ):
        now = datetime.now(timezone.utc)
        row_data = _make_row(
            mission_id, user_id, org_id,
            status="in_progress",
            started_at=now,
        )
        mock_pool.fetchrow.return_value = _make_mock_row(row_data)

        result = await repo.update_status(
            mission_id=mission_id,
            status="in_progress",
            started_at=now,
        )

        assert result.status == "in_progress"
        assert result.started_at == now


class TestGetStreak:
    async def test_returns_streak_count(
        self, repo, mock_pool, user_id,
    ):
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: 5 if key == "streak" else None
        mock_pool.fetchval.return_value = 5

        result = await repo.get_streak(user_id)

        assert result == 5
        call_args = mock_pool.fetchval.call_args
        sql = call_args[0][0]
        assert "$1" in sql

    async def test_returns_zero_when_no_missions(
        self, repo, mock_pool, user_id,
    ):
        mock_pool.fetchval.return_value = 0

        result = await repo.get_streak(user_id)

        assert result == 0
