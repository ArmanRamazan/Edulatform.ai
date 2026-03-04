from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.activity import Activity, ActivityType
from app.repositories.activity_repo import ActivityRepository
from app.services.activity_service import ActivityService


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_activity_repo():
    return AsyncMock(spec=ActivityRepository)


@pytest.fixture
def activity_service(mock_activity_repo):
    return ActivityService(repo=mock_activity_repo)


@pytest.fixture
def sample_activity(user_id):
    return Activity(
        id=uuid4(),
        user_id=user_id,
        activity_type="quiz_completed",
        payload={"quiz_id": str(uuid4()), "score": 0.8},
        created_at=datetime.now(timezone.utc),
    )


class TestRecordActivity:
    async def test_record_activity(
        self, activity_service, mock_activity_repo, user_id, sample_activity,
    ):
        mock_activity_repo.record_activity.return_value = sample_activity
        payload = {"quiz_id": str(uuid4()), "score": 0.8}

        result = await activity_service.record(
            user_id=user_id,
            activity_type=ActivityType.quiz_completed,
            payload=payload,
        )

        assert result == sample_activity
        mock_activity_repo.record_activity.assert_awaited_once_with(
            user_id, "quiz_completed", payload,
        )

    async def test_record_each_activity_type(
        self, activity_service, mock_activity_repo, user_id, sample_activity,
    ):
        mock_activity_repo.record_activity.return_value = sample_activity

        for activity_type in ActivityType:
            await activity_service.record(
                user_id=user_id,
                activity_type=activity_type,
                payload={},
            )

        assert mock_activity_repo.record_activity.await_count == len(ActivityType)


class TestGetMyActivity:
    async def test_get_my_activity_paginated(
        self, activity_service, mock_activity_repo, user_id,
    ):
        activities = [
            Activity(
                id=uuid4(), user_id=user_id,
                activity_type="quiz_completed",
                payload={"score": 0.9},
                created_at=datetime.now(timezone.utc),
            )
            for _ in range(3)
        ]
        mock_activity_repo.get_user_activities.return_value = activities

        result = await activity_service.get_my_activity(
            user_id=user_id, limit=20, offset=0,
        )

        assert result == activities
        mock_activity_repo.get_user_activities.assert_awaited_once_with(
            user_id, 20, 0,
        )

    async def test_get_my_activity_empty(
        self, activity_service, mock_activity_repo, user_id,
    ):
        mock_activity_repo.get_user_activities.return_value = []

        result = await activity_service.get_my_activity(
            user_id=user_id, limit=20, offset=0,
        )

        assert result == []


class TestGetSocialFeed:
    async def test_get_social_feed(
        self, activity_service, mock_activity_repo,
    ):
        user_ids = [uuid4(), uuid4()]
        activities = [
            Activity(
                id=uuid4(), user_id=user_ids[0],
                activity_type="badge_earned",
                payload={"badge_type": "streak_7"},
                created_at=datetime.now(timezone.utc),
            ),
            Activity(
                id=uuid4(), user_id=user_ids[1],
                activity_type="streak_milestone",
                payload={"streak": 14},
                created_at=datetime.now(timezone.utc),
            ),
        ]
        mock_activity_repo.get_feed_for_users.return_value = activities

        result = await activity_service.get_social_feed(
            user_ids=user_ids, limit=20, offset=0,
        )

        assert result == activities
        mock_activity_repo.get_feed_for_users.assert_awaited_once_with(
            user_ids, 20, 0,
        )

    async def test_get_social_feed_empty_user_ids(
        self, activity_service, mock_activity_repo,
    ):
        result = await activity_service.get_social_feed(
            user_ids=[], limit=20, offset=0,
        )

        assert result == []
        mock_activity_repo.get_feed_for_users.assert_not_awaited()
