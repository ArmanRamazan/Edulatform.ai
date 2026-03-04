import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import bcrypt as _bcrypt
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, NotFoundError
from common.security import create_access_token
from app.domain.user import User, UserRole, PublicProfile
from app.repositories.user_repo import UserRepository
from app.routes.profiles import router
from app.services.profile_service import ProfileService


# --- Fixtures ---


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def sample_user(user_id):
    return User(
        id=user_id,
        email="test@example.com",
        password_hash=_bcrypt.hashpw(b"password123", _bcrypt.gensalt()).decode(),
        name="Test User",
        role=UserRole.STUDENT,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
        email_verified=False,
    )


@pytest.fixture
def public_profile(user_id):
    return PublicProfile(
        id=user_id,
        name="Test User",
        bio=None,
        avatar_url=None,
        role=UserRole.STUDENT,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
        is_public=True,
    )


@pytest.fixture
def private_profile(user_id):
    return PublicProfile(
        id=user_id,
        name="Test User",
        bio=None,
        avatar_url=None,
        role=UserRole.STUDENT,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
        is_public=False,
    )


@pytest.fixture
def mock_profile_service():
    return AsyncMock(spec=ProfileService)


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def auth_token(user_id):
    return create_access_token(str(user_id), "test-secret")


@pytest.fixture
def test_app(mock_profile_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._profile_service = mock_profile_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# --- Service unit tests ---


class TestProfileServiceGetPublicProfile:
    async def test_success(self, mock_repo, public_profile):
        mock_repo.get_public_profile.return_value = public_profile
        service = ProfileService(repo=mock_repo)

        result = await service.get_public_profile(public_profile.id)

        assert result == public_profile
        mock_repo.get_public_profile.assert_called_once_with(public_profile.id)

    async def test_not_found(self, mock_repo):
        mock_repo.get_public_profile.return_value = None
        service = ProfileService(repo=mock_repo)

        with pytest.raises(NotFoundError):
            await service.get_public_profile(uuid4())


class TestProfileServiceGetUserStats:
    async def test_returns_stats(self, mock_repo, public_profile):
        mock_repo.get_public_profile.return_value = public_profile
        service = ProfileService(repo=mock_repo)

        result = await service.get_user_stats(public_profile.id)

        assert result["name"] == public_profile.name
        assert result["role"] == public_profile.role
        assert result["is_verified"] == public_profile.is_verified
        assert result["member_since"] == public_profile.created_at

    async def test_not_found(self, mock_repo):
        mock_repo.get_public_profile.return_value = None
        service = ProfileService(repo=mock_repo)

        with pytest.raises(NotFoundError):
            await service.get_user_stats(uuid4())


class TestProfileServiceUpdateVisibility:
    async def test_update(self, mock_repo, user_id):
        service = ProfileService(repo=mock_repo)

        await service.update_visibility(user_id, is_public=False)

        mock_repo.update_profile_visibility.assert_called_once_with(user_id, False)


# --- Route integration tests ---


class TestGetPublicProfileRoute:
    async def test_success(self, client, mock_profile_service, public_profile):
        mock_profile_service.get_public_profile.return_value = public_profile

        resp = await client.get(f"/users/{public_profile.id}/profile")

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test User"
        assert data["is_public"] is True
        assert "email" not in data
        assert "password_hash" not in data

    async def test_not_found(self, client, mock_profile_service):
        mock_profile_service.get_public_profile.side_effect = NotFoundError("User not found")

        resp = await client.get(f"/users/{uuid4()}/profile")

        assert resp.status_code == 404


class TestGetUserStatsRoute:
    async def test_success(self, client, mock_profile_service, public_profile):
        mock_profile_service.get_user_stats.return_value = {
            "name": public_profile.name,
            "role": public_profile.role,
            "is_verified": public_profile.is_verified,
            "member_since": public_profile.created_at,
        }

        resp = await client.get(f"/users/{public_profile.id}/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test User"
        assert data["role"] == "student"


class TestUpdateVisibilityRoute:
    async def test_success(self, client, mock_profile_service, auth_token):
        resp = await client.patch(
            "/users/me/visibility",
            json={"is_public": False},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert resp.status_code == 204
        mock_profile_service.update_visibility.assert_called_once()

    async def test_unauthenticated(self, client):
        resp = await client.patch(
            "/users/me/visibility",
            json={"is_public": False},
        )

        assert resp.status_code == 422 or resp.status_code == 401
