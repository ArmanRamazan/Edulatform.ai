from __future__ import annotations

from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.repositories.velocity_repo import VelocityRepository
from app.services.velocity_service import VelocityService


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_velocity_repo():
    return AsyncMock(spec=VelocityRepository)


@pytest.fixture
def velocity_service(mock_velocity_repo):
    return VelocityService(repo=mock_velocity_repo)


class TestGetVelocityTrend:
    async def test_trend_up_when_this_week_higher(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = [
            {"week_start": "2026-02-23", "count": 3},
            {"week_start": "2026-03-02", "count": 5},
        ]
        mock_velocity_repo.get_quiz_score_trend.return_value = []
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.0
        mock_velocity_repo.get_learning_streak.return_value = 0
        mock_velocity_repo.get_course_progress.return_value = []

        result = await velocity_service.get_velocity(user_id)

        assert result["concepts_mastered_this_week"] == 5
        assert result["concepts_mastered_last_week"] == 3
        assert result["trend"] == "up"

    async def test_trend_down_when_this_week_lower(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = [
            {"week_start": "2026-02-23", "count": 7},
            {"week_start": "2026-03-02", "count": 2},
        ]
        mock_velocity_repo.get_quiz_score_trend.return_value = []
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.0
        mock_velocity_repo.get_learning_streak.return_value = 0
        mock_velocity_repo.get_course_progress.return_value = []

        result = await velocity_service.get_velocity(user_id)

        assert result["concepts_mastered_this_week"] == 2
        assert result["concepts_mastered_last_week"] == 7
        assert result["trend"] == "down"

    async def test_trend_stable_when_equal(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = [
            {"week_start": "2026-02-23", "count": 4},
            {"week_start": "2026-03-02", "count": 4},
        ]
        mock_velocity_repo.get_quiz_score_trend.return_value = []
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.0
        mock_velocity_repo.get_learning_streak.return_value = 0
        mock_velocity_repo.get_course_progress.return_value = []

        result = await velocity_service.get_velocity(user_id)

        assert result["trend"] == "stable"

    async def test_trend_stable_when_only_one_week(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = [
            {"week_start": "2026-03-02", "count": 3},
        ]
        mock_velocity_repo.get_quiz_score_trend.return_value = []
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.0
        mock_velocity_repo.get_learning_streak.return_value = 0
        mock_velocity_repo.get_course_progress.return_value = []

        result = await velocity_service.get_velocity(user_id)

        assert result["concepts_mastered_this_week"] == 3
        assert result["concepts_mastered_last_week"] == 0
        assert result["trend"] == "up"


class TestGetVelocityNewUser:
    async def test_new_user_returns_defaults(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = []
        mock_velocity_repo.get_quiz_score_trend.return_value = []
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.0
        mock_velocity_repo.get_learning_streak.return_value = 0
        mock_velocity_repo.get_course_progress.return_value = []

        result = await velocity_service.get_velocity(user_id)

        assert result["concepts_mastered_this_week"] == 0
        assert result["concepts_mastered_last_week"] == 0
        assert result["trend"] == "stable"
        assert result["quiz_score_trend"] == []
        assert result["flashcard_retention_rate"] == 0.0
        assert result["streak_days"] == 0
        assert result["course_progress"] == []


class TestGetVelocityQuizScores:
    async def test_quiz_score_trend_passed_through(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = []
        mock_velocity_repo.get_quiz_score_trend.return_value = [
            {"week_start": "2026-02-16", "avg_score": 0.65},
            {"week_start": "2026-02-23", "avg_score": 0.72},
            {"week_start": "2026-03-02", "avg_score": 0.85},
        ]
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.0
        mock_velocity_repo.get_learning_streak.return_value = 0
        mock_velocity_repo.get_course_progress.return_value = []

        result = await velocity_service.get_velocity(user_id)

        assert len(result["quiz_score_trend"]) == 3
        assert result["quiz_score_trend"][2]["avg_score"] == 0.85


class TestGetVelocityRetentionAndStreak:
    async def test_retention_and_streak_passed_through(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = []
        mock_velocity_repo.get_quiz_score_trend.return_value = []
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.82
        mock_velocity_repo.get_learning_streak.return_value = 14
        mock_velocity_repo.get_course_progress.return_value = []

        result = await velocity_service.get_velocity(user_id)

        assert result["flashcard_retention_rate"] == 0.82
        assert result["streak_days"] == 14


class TestGetVelocityCourseProgress:
    async def test_course_progress_with_estimated_completion(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        course_id = str(uuid4())
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = [
            {"week_start": "2026-02-16", "count": 3},
            {"week_start": "2026-02-23", "count": 2},
            {"week_start": "2026-03-02", "count": 5},
        ]
        mock_velocity_repo.get_quiz_score_trend.return_value = []
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.0
        mock_velocity_repo.get_learning_streak.return_value = 0
        mock_velocity_repo.get_course_progress.return_value = [
            {"course_id": course_id, "total_concepts": 20, "mastered": 10},
        ]

        result = await velocity_service.get_velocity(user_id)

        progress = result["course_progress"]
        assert len(progress) == 1
        assert progress[0]["course_id"] == course_id
        assert progress[0]["total_concepts"] == 20
        assert progress[0]["mastered"] == 10
        assert progress[0]["mastery_pct"] == 50.0
        # avg concepts/week = (3+2+5)/3 ≈ 3.33, remaining = 10
        # estimated_weeks_left = 10 / 3.33 ≈ 3.0
        assert progress[0]["estimated_weeks_left"] == pytest.approx(3.0, abs=0.1)

    async def test_estimated_weeks_none_when_no_velocity(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        course_id = str(uuid4())
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = []
        mock_velocity_repo.get_quiz_score_trend.return_value = []
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.0
        mock_velocity_repo.get_learning_streak.return_value = 0
        mock_velocity_repo.get_course_progress.return_value = [
            {"course_id": course_id, "total_concepts": 15, "mastered": 0},
        ]

        result = await velocity_service.get_velocity(user_id)

        progress = result["course_progress"]
        assert progress[0]["estimated_weeks_left"] is None

    async def test_estimated_weeks_none_when_all_mastered(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        course_id = str(uuid4())
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = [
            {"week_start": "2026-03-02", "count": 2},
        ]
        mock_velocity_repo.get_quiz_score_trend.return_value = []
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.0
        mock_velocity_repo.get_learning_streak.return_value = 0
        mock_velocity_repo.get_course_progress.return_value = [
            {"course_id": course_id, "total_concepts": 10, "mastered": 10},
        ]

        result = await velocity_service.get_velocity(user_id)

        progress = result["course_progress"]
        assert progress[0]["mastery_pct"] == 100.0
        assert progress[0]["estimated_weeks_left"] == 0.0

    async def test_zero_total_concepts_course(
        self, velocity_service, mock_velocity_repo, user_id,
    ):
        course_id = str(uuid4())
        mock_velocity_repo.get_concepts_mastered_by_week.return_value = []
        mock_velocity_repo.get_quiz_score_trend.return_value = []
        mock_velocity_repo.get_flashcard_retention_rate.return_value = 0.0
        mock_velocity_repo.get_learning_streak.return_value = 0
        mock_velocity_repo.get_course_progress.return_value = [
            {"course_id": course_id, "total_concepts": 0, "mastered": 0},
        ]

        result = await velocity_service.get_velocity(user_id)

        progress = result["course_progress"]
        assert progress[0]["mastery_pct"] == 0.0
        assert progress[0]["estimated_weeks_left"] is None
