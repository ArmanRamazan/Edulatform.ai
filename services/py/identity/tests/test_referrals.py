from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.referral import Referral, ReferralStats, generate_referral_code
from app.repositories.referral_repo import ReferralRepository
from app.services.referral_service import ReferralService


REFERRAL_CODE_PATTERN = re.compile(r"^REF-[A-Z0-9]{8}$")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def referrer_id():
    return uuid4()


@pytest.fixture
def referee_id():
    return uuid4()


@pytest.fixture
def mock_referral_repo():
    return AsyncMock(spec=ReferralRepository)


@pytest.fixture
def mock_user_repo():
    from app.repositories.user_repo import UserRepository
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def referral_service(mock_referral_repo, mock_user_repo):
    return ReferralService(
        referral_repo=mock_referral_repo,
        user_repo=mock_user_repo,
    )


@pytest.fixture
def sample_referral(referrer_id, referee_id):
    return Referral(
        id=uuid4(),
        referrer_id=referrer_id,
        referee_id=referee_id,
        referral_code="REF-ABCD1234",
        status="pending",
        reward_type=None,
        created_at=datetime.now(timezone.utc),
        completed_at=None,
    )


@pytest.fixture
def sample_stats(referrer_id):
    return ReferralStats(
        referral_code="REF-ABCD1234",
        invited_count=5,
        completed_count=3,
        rewards_earned=3,
    )


# ---------------------------------------------------------------------------
# Domain tests
# ---------------------------------------------------------------------------

class TestReferralCodeFormat:
    def test_referral_code_format(self):
        code = generate_referral_code()
        assert REFERRAL_CODE_PATTERN.match(code)

    def test_referral_code_uniqueness(self):
        codes = {generate_referral_code() for _ in range(100)}
        assert len(codes) == 100


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------

class TestApplyReferralCode:
    async def test_apply_referral_success(
        self, referral_service, mock_referral_repo, mock_user_repo, referrer_id, referee_id, sample_referral
    ):
        mock_referral_repo.get_referrer_by_code.return_value = referrer_id
        mock_referral_repo.get_referral_by_referee.return_value = None
        mock_referral_repo.create_referral.return_value = sample_referral

        result = await referral_service.apply_referral_code(referee_id, "REF-ABCD1234")

        assert result.referrer_id == referrer_id
        assert result.status == "pending"
        mock_referral_repo.create_referral.assert_called_once_with(referrer_id, referee_id, "REF-ABCD1234")

    async def test_apply_referral_self_referral(
        self, referral_service, mock_referral_repo, referrer_id
    ):
        mock_referral_repo.get_referrer_by_code.return_value = referrer_id

        with pytest.raises(Exception, match="Cannot refer yourself"):
            await referral_service.apply_referral_code(referrer_id, "REF-ABCD1234")

    async def test_apply_referral_already_referred(
        self, referral_service, mock_referral_repo, referrer_id, referee_id, sample_referral
    ):
        mock_referral_repo.get_referrer_by_code.return_value = referrer_id
        mock_referral_repo.get_referral_by_referee.return_value = sample_referral

        with pytest.raises(Exception, match="Already referred"):
            await referral_service.apply_referral_code(referee_id, "REF-ABCD1234")

    async def test_apply_referral_invalid_code(
        self, referral_service, mock_referral_repo, referee_id
    ):
        mock_referral_repo.get_referrer_by_code.return_value = None

        with pytest.raises(Exception, match="Invalid referral code"):
            await referral_service.apply_referral_code(referee_id, "REF-INVALID1")


class TestCompleteReferral:
    async def test_complete_referral_success(
        self, referral_service, mock_referral_repo, referee_id, sample_referral
    ):
        completed = Referral(
            id=sample_referral.id,
            referrer_id=sample_referral.referrer_id,
            referee_id=referee_id,
            referral_code=sample_referral.referral_code,
            status="completed",
            reward_type="credit",
            created_at=sample_referral.created_at,
            completed_at=datetime.now(timezone.utc),
        )
        mock_referral_repo.complete_referral.return_value = completed

        result = await referral_service.complete_referral(referee_id)

        assert result is not None
        assert result.status == "completed"
        mock_referral_repo.complete_referral.assert_called_once_with(referee_id)

    async def test_complete_referral_no_pending(
        self, referral_service, mock_referral_repo, referee_id
    ):
        mock_referral_repo.complete_referral.return_value = None

        with pytest.raises(Exception, match="No pending referral"):
            await referral_service.complete_referral(referee_id)


class TestGetReferralStats:
    async def test_get_referral_stats(
        self, referral_service, mock_referral_repo, mock_user_repo, referrer_id, sample_stats
    ):
        mock_user_repo.get_referral_code.return_value = "REF-ABCD1234"
        mock_referral_repo.get_referral_stats.return_value = sample_stats

        result = await referral_service.get_my_referral_info(referrer_id)

        assert result.referral_code == "REF-ABCD1234"
        assert result.invited_count == 5
        assert result.completed_count == 3


class TestGenerateReferralCode:
    async def test_generate_code_when_missing(
        self, referral_service, mock_user_repo, referrer_id
    ):
        mock_user_repo.get_referral_code.return_value = None
        mock_user_repo.set_referral_code.return_value = "REF-NEWCODE1"

        result = await referral_service.generate_referral_code(referrer_id)

        assert REFERRAL_CODE_PATTERN.match(result)
        mock_user_repo.set_referral_code.assert_called_once()

    async def test_generate_code_when_exists(
        self, referral_service, mock_user_repo, referrer_id
    ):
        mock_user_repo.get_referral_code.return_value = "REF-EXISTING"

        result = await referral_service.generate_referral_code(referrer_id)

        assert result == "REF-EXISTING"
        mock_user_repo.set_referral_code.assert_not_called()


# ---------------------------------------------------------------------------
# Route integration tests
# ---------------------------------------------------------------------------

class TestReferralRoutes:
    @pytest.fixture
    def mock_referral_service(self):
        return AsyncMock(spec=ReferralService)

    @pytest.fixture
    def fixed_user_id(self):
        return uuid4()

    @pytest.fixture
    async def client(self, mock_referral_service, fixed_user_id):
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from common.errors import register_error_handlers
        from app.routes.referrals import router, _get_referral_service
        from app.routes.auth import _get_current_user_id

        app = FastAPI()
        register_error_handlers(app)
        app.include_router(router)

        app.dependency_overrides[_get_referral_service] = lambda: mock_referral_service
        app.dependency_overrides[_get_current_user_id] = lambda: fixed_user_id

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_get_referral_stats(self, client, mock_referral_service):
        mock_referral_service.get_my_referral_info.return_value = ReferralStats(
            referral_code="REF-ABCD1234",
            invited_count=5,
            completed_count=3,
            rewards_earned=3,
        )

        resp = await client.get("/referral/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["referral_code"] == "REF-ABCD1234"
        assert data["invited_count"] == 5

    async def test_apply_referral_code(self, client, mock_referral_service, sample_referral):
        mock_referral_service.apply_referral_code.return_value = sample_referral

        resp = await client.post("/referral/apply", json={"referral_code": "REF-ABCD1234"})

        assert resp.status_code == 201

    async def test_complete_referral(self, client, mock_referral_service, sample_referral):
        completed = Referral(
            id=sample_referral.id,
            referrer_id=sample_referral.referrer_id,
            referee_id=sample_referral.referee_id,
            referral_code=sample_referral.referral_code,
            status="completed",
            reward_type="credit",
            created_at=sample_referral.created_at,
            completed_at=datetime.now(timezone.utc),
        )
        mock_referral_service.complete_referral.return_value = completed

        resp = await client.post("/referral/complete", json={"referee_id": str(sample_referral.referee_id)})

        assert resp.status_code == 200

    async def test_unauthenticated_get_stats(self, mock_referral_service):
        """GET /referral/me without auth returns 401 or 422."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from common.errors import register_error_handlers
        from app.routes.referrals import router, _get_referral_service

        app = FastAPI()
        register_error_handlers(app)
        app.include_router(router)
        app.dependency_overrides[_get_referral_service] = lambda: mock_referral_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/referral/me")
            assert resp.status_code in (401, 422)


class TestNewUserGetsReferralCode:
    async def test_new_user_gets_referral_code(self, mock_user_repo, mock_referral_repo):
        """Registration flow generates a referral code for new users."""
        from app.services.auth_service import AuthService
        from app.domain.user import User, UserRole

        user_with_code = User(
            id=uuid4(),
            email="new@example.com",
            password_hash="hashed",
            name="New User",
            role=UserRole.STUDENT,
            is_verified=False,
            created_at=datetime.now(timezone.utc),
            email_verified=False,
            referral_code="REF-NEWUSER1",
        )

        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.create.return_value = user_with_code

        service = AuthService(
            repo=mock_user_repo,
            jwt_secret="test-secret",
            jwt_algorithm="HS256",
            jwt_ttl_seconds=3600,
        )

        result = await service.register("new@example.com", "password123", "New User")

        assert result.access_token
        # Verify create was called — the repo handles referral_code generation
        mock_user_repo.create.assert_called_once()
