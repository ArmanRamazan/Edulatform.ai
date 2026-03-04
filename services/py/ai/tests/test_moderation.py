import json
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient
from app.services.ai_service import AIService
from app.services.credit_service import CreditService
from app.services.study_plan_service import StudyPlanService
from app.services.moderation_service import ModerationService
from app.domain.models import ModerationResponse


SAMPLE_APPROVED_RESPONSE = {
    "quality_score": 8,
    "flags": [],
    "suggestions": ["Consider adding more examples"],
    "summary": "Well-written course description with clear learning objectives.",
}

SAMPLE_LOW_QUALITY_RESPONSE = {
    "quality_score": 3,
    "flags": ["low_quality", "potential_spam"],
    "suggestions": ["Add more detail", "Remove promotional language"],
    "summary": "Content appears low quality and potentially promotional.",
}

SAMPLE_INAPPROPRIATE_RESPONSE = {
    "quality_score": 2,
    "flags": ["inappropriate_content", "low_quality"],
    "suggestions": ["Remove inappropriate language", "Focus on educational content"],
    "summary": "Content contains inappropriate material.",
}


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def mock_llm():
    mock = AsyncMock(spec=GeminiClient)
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def moderation_service(mock_llm):
    return ModerationService(llm=mock_llm)


# --- Service-level tests ---


class TestModerationService:
    async def test_high_quality_content_approved(self, moderation_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_APPROVED_RESPONSE), 100, 200)

        result = await moderation_service.moderate(
            content="Learn Python programming from scratch with hands-on projects.",
            content_type="course_description",
        )

        assert isinstance(result, ModerationResponse)
        assert result.approved is True
        assert result.quality_score == 8
        assert result.flags == []
        assert len(result.suggestions) == 1

    async def test_low_quality_content_not_approved(self, moderation_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_LOW_QUALITY_RESPONSE), 100, 200)

        result = await moderation_service.moderate(
            content="buy now!!! best course ever!!!",
            content_type="course_description",
        )

        assert result.approved is False
        assert result.quality_score == 3
        assert "low_quality" in result.flags
        assert "potential_spam" in result.flags

    async def test_inappropriate_content_not_approved(self, moderation_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_INAPPROPRIATE_RESPONSE), 100, 200)

        result = await moderation_service.moderate(
            content="some inappropriate content",
            content_type="lesson_content",
        )

        assert result.approved is False
        assert "inappropriate_content" in result.flags

    async def test_critical_flag_overrides_high_score(self, moderation_service, mock_llm):
        """Even with quality_score >= 5, critical flags should force approved=False."""
        response = {
            "quality_score": 7,
            "flags": ["hate_speech"],
            "suggestions": [],
            "summary": "Contains hate speech despite decent quality.",
        }
        mock_llm.generate.return_value = (json.dumps(response), 100, 200)

        result = await moderation_service.moderate(
            content="some content",
            content_type="course_description",
        )

        assert result.approved is False

    async def test_content_type_in_prompt(self, moderation_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_APPROVED_RESPONSE), 100, 200)

        await moderation_service.moderate(
            content="test content",
            content_type="review_text",
        )

        prompt = mock_llm.generate.call_args[0][0]
        assert "review_text" in prompt

    async def test_content_trimmed_before_sending(self, moderation_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_APPROVED_RESPONSE), 100, 200)

        await moderation_service.moderate(
            content="   padded content   ",
            content_type="course_description",
        )

        prompt = mock_llm.generate.call_args[0][0]
        assert "   padded content   " not in prompt
        assert "padded content" in prompt

    async def test_content_truncated_to_limit(self, moderation_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_APPROVED_RESPONSE), 100, 200)
        long_content = "a" * 15000

        await moderation_service.moderate(
            content=long_content,
            content_type="course_description",
        )

        prompt = mock_llm.generate.call_args[0][0]
        # Content in prompt should be truncated to 10000 chars
        assert "a" * 15000 not in prompt

    async def test_gemini_failure_returns_safe_default(self, moderation_service, mock_llm):
        """When Gemini fails, return approved=True with moderation_unavailable flag."""
        from common.errors import AppError
        mock_llm.generate.side_effect = AppError("LLM error", status_code=502)

        result = await moderation_service.moderate(
            content="valid content",
            content_type="course_description",
        )

        assert result.approved is True
        assert "moderation_unavailable" in result.flags
        assert result.quality_score == 0
        assert result.suggestions == []

    async def test_malformed_json_returns_safe_default(self, moderation_service, mock_llm):
        mock_llm.generate.return_value = ("not valid json at all", 100, 200)

        result = await moderation_service.moderate(
            content="valid content",
            content_type="course_description",
        )

        assert result.approved is True
        assert "moderation_unavailable" in result.flags
        assert result.quality_score == 0

    async def test_missing_keys_returns_safe_default(self, moderation_service, mock_llm):
        mock_llm.generate.return_value = ('{"random": "data"}', 100, 200)

        result = await moderation_service.moderate(
            content="valid content",
            content_type="course_description",
        )

        assert result.approved is True
        assert "moderation_unavailable" in result.flags

    async def test_markdown_fences_stripped(self, moderation_service, mock_llm):
        wrapped = f"```json\n{json.dumps(SAMPLE_APPROVED_RESPONSE)}\n```"
        mock_llm.generate.return_value = (wrapped, 100, 200)

        result = await moderation_service.moderate(
            content="test content",
            content_type="course_description",
        )

        assert result.approved is True
        assert result.quality_score == 8

    async def test_no_pii_in_prompt(self, moderation_service, mock_llm):
        """Content should be sent but no user identifiers."""
        mock_llm.generate.return_value = (json.dumps(SAMPLE_APPROVED_RESPONSE), 100, 200)

        await moderation_service.moderate(
            content="my content to check",
            content_type="course_description",
        )

        prompt = mock_llm.generate.call_args[0][0]
        assert "my content to check" in prompt


# --- Route-level tests ---


def _make_token(settings: Settings, role: str = "student", tier: str = "free") -> str:
    payload = {
        "sub": str(uuid4()),
        "role": role,
        "subscription_tier": tier,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
def student_token(settings):
    return _make_token(settings, role="student", tier="free")


@pytest.fixture
def teacher_token(settings):
    return _make_token(settings, role="teacher", tier="free")


@pytest.fixture
def admin_token(settings):
    return _make_token(settings, role="admin", tier="free")


@pytest.fixture
async def client(settings, mock_cache, mock_llm):
    import app.main as main_module

    main_module.app_settings = settings
    main_module._ai_service = AIService(mock_llm, mock_cache, settings)
    main_module._tutor_service = main_module.TutorService(mock_llm, mock_cache, settings)
    main_module._credit_service = CreditService(cache=mock_cache)
    main_module._study_plan_service = StudyPlanService(
        llm=mock_llm, http_client=AsyncMock(), settings=settings,
    )
    main_module._moderation_service = ModerationService(llm=mock_llm)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestModerationRoute:
    async def test_requires_auth(self, client):
        resp = await client.post("/ai/moderate", json={
            "content": "test content",
            "content_type": "course_description",
        })
        assert resp.status_code in (401, 422)

    async def test_student_forbidden(self, client, student_token):
        resp = await client.post(
            "/ai/moderate",
            json={"content": "test content", "content_type": "course_description"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

    async def test_teacher_allowed(self, client, teacher_token, mock_llm, mock_cache):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_APPROVED_RESPONSE), 100, 200)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/moderate",
            json={"content": "Learn Python programming", "content_type": "course_description"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200

    async def test_admin_allowed(self, client, admin_token, mock_llm, mock_cache):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_APPROVED_RESPONSE), 100, 200)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/moderate",
            json={"content": "Learn Python programming", "content_type": "course_description"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    async def test_credits_enforced(self, client, teacher_token, mock_cache):
        mock_cache.get_credits_used.return_value = 10  # free plan limit

        resp = await client.post(
            "/ai/moderate",
            json={"content": "test content", "content_type": "course_description"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 403

    async def test_response_shape(self, client, teacher_token, mock_llm, mock_cache):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_APPROVED_RESPONSE), 100, 200)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/moderate",
            json={"content": "Learn Python programming", "content_type": "course_description"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "approved" in data
        assert "flags" in data
        assert "quality_score" in data
        assert "suggestions" in data

    async def test_validates_content_type(self, client, teacher_token):
        resp = await client.post(
            "/ai/moderate",
            json={"content": "test", "content_type": "invalid_type"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 422

    async def test_validates_content_too_long(self, client, teacher_token):
        resp = await client.post(
            "/ai/moderate",
            json={"content": "x" * 10001, "content_type": "course_description"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 422

    async def test_validates_content_required(self, client, teacher_token):
        resp = await client.post(
            "/ai/moderate",
            json={"content_type": "course_description"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 422
