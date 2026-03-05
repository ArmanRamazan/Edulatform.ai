from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.trust_level import (
    LEVEL_NAMES,
    LEVEL_THRESHOLDS,
    TrustLevel,
)
from app.repositories.trust_level_repo import TrustLevelRepository
from app.services.trust_level_service import TrustLevelService


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def mock_trust_repo():
    return AsyncMock(spec=TrustLevelRepository)


@pytest.fixture
def trust_service(mock_trust_repo):
    return TrustLevelService(repo=mock_trust_repo)


def _make_trust_level(
    user_id,
    org_id,
    level: int = 0,
    missions: int = 0,
    concepts: int = 0,
    unlocked_areas: list[str] | None = None,
    level_up_at: datetime | None = None,
) -> TrustLevel:
    return TrustLevel(
        id=uuid4(),
        user_id=user_id,
        organization_id=org_id,
        level=level,
        total_missions_completed=missions,
        total_concepts_mastered=concepts,
        unlocked_areas=unlocked_areas or [],
        level_up_at=level_up_at,
        created_at=datetime.now(timezone.utc),
    )


# --- Domain tests ---


class TestLevelThresholds:
    def test_five_levels_defined(self):
        assert set(LEVEL_THRESHOLDS.keys()) == {1, 2, 3, 4, 5}

    def test_thresholds_are_monotonically_increasing(self):
        prev_missions = 0
        prev_concepts = 0
        for lvl in range(1, 6):
            t = LEVEL_THRESHOLDS[lvl]
            assert t["missions"] > prev_missions
            assert t["concepts_mastered"] > prev_concepts
            prev_missions = t["missions"]
            prev_concepts = t["concepts_mastered"]

    def test_level_names_include_zero_through_five(self):
        assert set(LEVEL_NAMES.keys()) == {0, 1, 2, 3, 4, 5}
        assert LEVEL_NAMES[0] == "Newcomer"
        assert LEVEL_NAMES[5] == "Architect"

    def test_trust_level_is_frozen(self):
        tl = _make_trust_level(uuid4(), uuid4())
        with pytest.raises(AttributeError):
            tl.level = 1  # type: ignore[misc]


# --- Service: check_level_up ---


class TestCheckLevelUp:
    def test_no_level_up_when_below_threshold(self, trust_service):
        tl = _make_trust_level(uuid4(), uuid4(), level=0, missions=2, concepts=1)
        result = trust_service.check_level_up(tl)
        assert result is None

    def test_level_up_to_1_when_threshold_met(self, trust_service):
        tl = _make_trust_level(uuid4(), uuid4(), level=0, missions=5, concepts=3)
        result = trust_service.check_level_up(tl)
        assert result == 1

    def test_level_up_to_2_when_threshold_met(self, trust_service):
        tl = _make_trust_level(uuid4(), uuid4(), level=1, missions=15, concepts=8)
        result = trust_service.check_level_up(tl)
        assert result == 2

    def test_level_up_to_3(self, trust_service):
        tl = _make_trust_level(uuid4(), uuid4(), level=2, missions=30, concepts=15)
        result = trust_service.check_level_up(tl)
        assert result == 3

    def test_level_up_to_4(self, trust_service):
        tl = _make_trust_level(uuid4(), uuid4(), level=3, missions=50, concepts=25)
        result = trust_service.check_level_up(tl)
        assert result == 4

    def test_level_up_to_5(self, trust_service):
        tl = _make_trust_level(uuid4(), uuid4(), level=4, missions=80, concepts=40)
        result = trust_service.check_level_up(tl)
        assert result == 5

    def test_no_level_up_at_max(self, trust_service):
        tl = _make_trust_level(uuid4(), uuid4(), level=5, missions=100, concepts=50)
        result = trust_service.check_level_up(tl)
        assert result is None

    def test_missions_met_but_not_concepts(self, trust_service):
        tl = _make_trust_level(uuid4(), uuid4(), level=0, missions=5, concepts=2)
        result = trust_service.check_level_up(tl)
        assert result is None

    def test_concepts_met_but_not_missions(self, trust_service):
        tl = _make_trust_level(uuid4(), uuid4(), level=0, missions=4, concepts=3)
        result = trust_service.check_level_up(tl)
        assert result is None

    def test_skip_levels_when_far_ahead(self, trust_service):
        """If user somehow has enough for level 3 but is at 0, should level up to 3."""
        tl = _make_trust_level(uuid4(), uuid4(), level=0, missions=30, concepts=15)
        result = trust_service.check_level_up(tl)
        assert result == 3


# --- Service: get_my_level ---


class TestGetMyLevel:
    async def test_returns_existing_trust_level(
        self, trust_service, mock_trust_repo, user_id, org_id,
    ):
        tl = _make_trust_level(user_id, org_id, level=2, missions=20, concepts=10)
        mock_trust_repo.get_or_create.return_value = tl

        result = await trust_service.get_my_level(user_id, org_id)

        assert result.level == 2
        assert result.total_missions_completed == 20
        mock_trust_repo.get_or_create.assert_awaited_once_with(user_id, org_id)


# --- Service: record_mission_completed ---


class TestRecordMissionCompleted:
    async def test_increments_and_no_level_up(
        self, trust_service, mock_trust_repo, user_id, org_id,
    ):
        after_increment = _make_trust_level(
            user_id, org_id, level=0, missions=3, concepts=1,
        )
        mock_trust_repo.get_or_create.return_value = _make_trust_level(
            user_id, org_id, level=0, missions=2, concepts=1,
        )
        mock_trust_repo.increment_missions.return_value = after_increment

        result = await trust_service.record_mission_completed(user_id, org_id)

        assert result.total_missions_completed == 3
        mock_trust_repo.increment_missions.assert_awaited_once_with(user_id)
        mock_trust_repo.update_level.assert_not_awaited()

    async def test_increments_and_levels_up(
        self, trust_service, mock_trust_repo, user_id, org_id,
    ):
        after_increment = _make_trust_level(
            user_id, org_id, level=0, missions=5, concepts=3,
        )
        leveled_up = _make_trust_level(
            user_id, org_id, level=1, missions=5, concepts=3,
        )
        mock_trust_repo.get_or_create.return_value = _make_trust_level(
            user_id, org_id, level=0, missions=4, concepts=3,
        )
        mock_trust_repo.increment_missions.return_value = after_increment
        mock_trust_repo.update_level.return_value = leveled_up

        result = await trust_service.record_mission_completed(user_id, org_id)

        assert result.level == 1
        mock_trust_repo.update_level.assert_awaited_once()


# --- Service: record_concept_mastered ---


class TestRecordConceptMastered:
    async def test_increments_and_no_level_up(
        self, trust_service, mock_trust_repo, user_id, org_id,
    ):
        after_increment = _make_trust_level(
            user_id, org_id, level=0, missions=5, concepts=2,
        )
        mock_trust_repo.get_or_create.return_value = _make_trust_level(
            user_id, org_id, level=0, missions=5, concepts=1,
        )
        mock_trust_repo.increment_concepts.return_value = after_increment

        result = await trust_service.record_concept_mastered(user_id, org_id)

        assert result.total_concepts_mastered == 2
        mock_trust_repo.increment_concepts.assert_awaited_once_with(user_id)
        mock_trust_repo.update_level.assert_not_awaited()

    async def test_increments_and_levels_up(
        self, trust_service, mock_trust_repo, user_id, org_id,
    ):
        after_increment = _make_trust_level(
            user_id, org_id, level=0, missions=5, concepts=3,
        )
        leveled_up = _make_trust_level(
            user_id, org_id, level=1, missions=5, concepts=3,
        )
        mock_trust_repo.get_or_create.return_value = _make_trust_level(
            user_id, org_id, level=0, missions=5, concepts=2,
        )
        mock_trust_repo.increment_concepts.return_value = after_increment
        mock_trust_repo.update_level.return_value = leveled_up

        result = await trust_service.record_concept_mastered(user_id, org_id)

        assert result.level == 1
        mock_trust_repo.update_level.assert_awaited_once()
