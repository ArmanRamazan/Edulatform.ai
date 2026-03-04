from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from common.errors import AppError, ConflictError, NotFoundError, register_error_handlers
from app.domain.follow import Follow, FollowStats
from app.services.follow_service import FollowService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def follower_id():
    return uuid4()


@pytest.fixture
def following_id():
    return uuid4()


@pytest.fixture
def sample_follow(follower_id, following_id):
    return Follow(
        id=uuid4(),
        follower_id=follower_id,
        following_id=following_id,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_follow_repo():
    from app.repositories.follow_repo import FollowRepository
    return AsyncMock(spec=FollowRepository)


@pytest.fixture
def mock_user_repo():
    from app.repositories.user_repo import UserRepository
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def follow_service(mock_follow_repo, mock_user_repo):
    return FollowService(follow_repo=mock_follow_repo, user_repo=mock_user_repo)


@pytest.fixture
def mock_follow_service():
    return AsyncMock(spec=FollowService)


@pytest.fixture
def fixed_user_id():
    return uuid4()


@pytest.fixture
async def client(mock_follow_service, fixed_user_id):
    from app.routes.follows import router, _get_follow_service, _get_current_user_id

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    app.dependency_overrides[_get_follow_service] = lambda: mock_follow_service
    app.dependency_overrides[_get_current_user_id] = lambda: fixed_user_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------

class TestFollowServiceFollow:
    async def test_follow_user_success(
        self, follow_service, mock_follow_repo, mock_user_repo, follower_id, following_id, sample_follow
    ):
        mock_user_repo.get_by_id.return_value = True  # target exists
        mock_follow_repo.follow.return_value = sample_follow

        result = await follow_service.follow_user(follower_id, following_id)

        assert result.follower_id == follower_id
        mock_follow_repo.follow.assert_called_once_with(follower_id, following_id)

    async def test_follow_self_raises(self, follow_service, follower_id):
        with pytest.raises(AppError, match="Cannot follow yourself"):
            await follow_service.follow_user(follower_id, follower_id)

    async def test_follow_nonexistent_user(self, follow_service, mock_user_repo, follower_id, following_id):
        mock_user_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="User not found"):
            await follow_service.follow_user(follower_id, following_id)


class TestFollowServiceUnfollow:
    async def test_unfollow_success(self, follow_service, mock_follow_repo, follower_id, following_id):
        mock_follow_repo.unfollow.return_value = True

        await follow_service.unfollow_user(follower_id, following_id)

        mock_follow_repo.unfollow.assert_called_once_with(follower_id, following_id)

    async def test_unfollow_not_following(self, follow_service, mock_follow_repo, follower_id, following_id):
        mock_follow_repo.unfollow.return_value = False

        with pytest.raises(NotFoundError, match="Not following this user"):
            await follow_service.unfollow_user(follower_id, following_id)


class TestFollowServiceQueries:
    async def test_get_followers_paginated(self, follow_service, mock_follow_repo, follower_id, sample_follow):
        mock_follow_repo.get_followers.return_value = ([sample_follow], 1)

        items, total = await follow_service.get_followers(follower_id, limit=20, offset=0)

        assert len(items) == 1
        assert total == 1
        mock_follow_repo.get_followers.assert_called_once_with(follower_id, 20, 0)

    async def test_get_following_paginated(self, follow_service, mock_follow_repo, follower_id, sample_follow):
        mock_follow_repo.get_following.return_value = ([sample_follow], 1)

        items, total = await follow_service.get_following(follower_id, limit=20, offset=0)

        assert len(items) == 1
        assert total == 1
        mock_follow_repo.get_following.assert_called_once_with(follower_id, 20, 0)

    async def test_get_follow_counts(self, follow_service, mock_follow_repo, follower_id):
        mock_follow_repo.count_followers.return_value = 10
        mock_follow_repo.count_following.return_value = 5

        stats = await follow_service.get_follow_counts(follower_id)

        assert stats.followers_count == 10
        assert stats.following_count == 5


# ---------------------------------------------------------------------------
# Route integration tests
# ---------------------------------------------------------------------------

class TestFollowRoutes:
    async def test_follow_user_201(self, client, mock_follow_service, fixed_user_id):
        target_id = uuid4()
        mock_follow_service.follow_user.return_value = Follow(
            id=uuid4(),
            follower_id=fixed_user_id,
            following_id=target_id,
            created_at=datetime.now(timezone.utc),
        )

        resp = await client.post(f"/follow/{target_id}")

        assert resp.status_code == 201
        data = resp.json()
        assert data["following_id"] == str(target_id)
        mock_follow_service.follow_user.assert_called_once_with(fixed_user_id, target_id)

    async def test_follow_self_400(self, client, mock_follow_service, fixed_user_id):
        mock_follow_service.follow_user.side_effect = AppError("Cannot follow yourself")

        resp = await client.post(f"/follow/{fixed_user_id}")

        assert resp.status_code == 400

    async def test_follow_duplicate_409(self, client, mock_follow_service):
        target_id = uuid4()
        mock_follow_service.follow_user.side_effect = ConflictError("Already following this user")

        resp = await client.post(f"/follow/{target_id}")

        assert resp.status_code == 409

    async def test_follow_nonexistent_404(self, client, mock_follow_service):
        target_id = uuid4()
        mock_follow_service.follow_user.side_effect = NotFoundError("User not found")

        resp = await client.post(f"/follow/{target_id}")

        assert resp.status_code == 404

    async def test_unfollow_204(self, client, mock_follow_service):
        target_id = uuid4()

        resp = await client.delete(f"/follow/{target_id}")

        assert resp.status_code == 204

    async def test_unfollow_not_following_404(self, client, mock_follow_service):
        target_id = uuid4()
        mock_follow_service.unfollow_user.side_effect = NotFoundError("Not following this user")

        resp = await client.delete(f"/follow/{target_id}")

        assert resp.status_code == 404

    async def test_get_followers_paginated(self, client, mock_follow_service, fixed_user_id):
        follow = Follow(
            id=uuid4(),
            follower_id=uuid4(),
            following_id=fixed_user_id,
            created_at=datetime.now(timezone.utc),
        )
        mock_follow_service.get_followers.return_value = ([follow], 1)

        resp = await client.get("/followers/me?limit=20&offset=0")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_get_following_paginated(self, client, mock_follow_service, fixed_user_id):
        follow = Follow(
            id=uuid4(),
            follower_id=fixed_user_id,
            following_id=uuid4(),
            created_at=datetime.now(timezone.utc),
        )
        mock_follow_service.get_following.return_value = ([follow], 1)

        resp = await client.get("/following/me?limit=20&offset=0")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_get_follow_counts(self, client, mock_follow_service):
        target_id = uuid4()
        mock_follow_service.get_follow_counts.return_value = FollowStats(
            followers_count=10, following_count=5
        )

        resp = await client.get(f"/users/{target_id}/followers/count")

        assert resp.status_code == 200
        data = resp.json()
        assert data["followers_count"] == 10
        assert data["following_count"] == 5

    async def test_follow_unauthenticated_401(self, mock_follow_service):
        """Test that requests without a valid token get 401."""
        from app.routes.follows import router

        app = FastAPI()
        register_error_handlers(app)
        app.include_router(router)

        # Do NOT override _get_current_user_id so the real one runs (no header → 401)
        from app.routes.follows import _get_follow_service
        app.dependency_overrides[_get_follow_service] = lambda: mock_follow_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(f"/follow/{uuid4()}")
            assert resp.status_code in (401, 422)
