from uuid import uuid4
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient
from app.services.credit_service import CreditService


@pytest.fixture
def settings():
    return Settings()


def _make_token(settings: Settings, user_id: str | None = None, tier: str = "free") -> str:
    payload = {
        "sub": user_id or str(uuid4()),
        "role": "student",
        "subscription_tier": tier,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def mock_llm():
    mock = AsyncMock(spec=GeminiClient)
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


@pytest.fixture
async def client(settings, mock_cache, mock_llm):
    import app.main as main_module

    credit_svc = CreditService(cache=mock_cache)

    main_module.app_settings = settings
    main_module._ai_service = main_module.AIService(mock_llm, mock_cache, settings)
    main_module._tutor_service = main_module.TutorService(mock_llm, mock_cache, settings)
    main_module._credit_service = credit_svc

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestCreditsMe:
    async def test_returns_credit_status(self, client, settings, mock_cache):
        mock_cache.get_credits_used.return_value = 3
        token = _make_token(settings, tier="free")

        resp = await client.get(
            "/ai/credits/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["used"] == 3
        assert data["limit"] == 10
        assert data["remaining"] == 7
        assert data["tier"] == "free"
        assert "reset_at" in data

    async def test_pro_tier_from_jwt(self, client, settings, mock_cache):
        mock_cache.get_credits_used.return_value = 500
        token = _make_token(settings, tier="pro")

        resp = await client.get(
            "/ai/credits/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == -1
        assert data["remaining"] == 999999
        assert data["tier"] == "pro"

    async def test_missing_tier_defaults_to_free(self, client, settings, mock_cache):
        mock_cache.get_credits_used.return_value = 0
        payload = {"sub": str(uuid4()), "role": "student"}  # no subscription_tier
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        resp = await client.get(
            "/ai/credits/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        assert resp.json()["tier"] == "free"


class TestCreditEnforcementOnEndpoints:
    async def test_quiz_generate_403_when_exhausted(self, client, settings, mock_cache):
        mock_cache.get_credits_used.return_value = 10  # free limit
        token = _make_token(settings, tier="free")

        resp = await client.post(
            "/ai/quiz/generate",
            json={"lesson_id": str(uuid4()), "content": "A" * 100},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403

    async def test_summary_generate_403_when_exhausted(self, client, settings, mock_cache):
        mock_cache.get_credits_used.return_value = 10
        token = _make_token(settings, tier="free")

        resp = await client.post(
            "/ai/summary/generate",
            json={"lesson_id": str(uuid4()), "content": "A" * 100},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403

    async def test_tutor_chat_403_when_exhausted(self, client, settings, mock_cache):
        mock_cache.get_credits_used.return_value = 10
        token = _make_token(settings, tier="free")

        resp = await client.post(
            "/ai/tutor/chat",
            json={
                "lesson_id": str(uuid4()),
                "message": "Hello",
                "lesson_content": "A" * 100,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403

    async def test_tutor_feedback_no_credit_check(self, client, settings, mock_cache):
        """Feedback endpoint should NOT consume credits."""
        mock_cache.get_credits_used.return_value = 10  # at limit
        mock_cache.get_conversation.return_value = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]
        token = _make_token(settings, tier="free")

        resp = await client.post(
            "/ai/tutor/feedback",
            json={"session_id": "sess-1", "message_index": 1, "rating": 1},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
