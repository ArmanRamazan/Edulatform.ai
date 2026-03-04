import json
import math
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient
from app.services.ai_service import AIService
from app.services.credit_service import CreditService
from app.services.study_plan_service import StudyPlanService
from app.domain.models import StudyPlanResponse


SAMPLE_MASTERY_RESPONSE = {
    "concepts": [
        {"concept_id": str(uuid4()), "name": "Variables", "mastery_level": 0.8},
        {"concept_id": str(uuid4()), "name": "Loops", "mastery_level": 0.3},
        {"concept_id": str(uuid4()), "name": "Functions", "mastery_level": 0.5},
        {"concept_id": str(uuid4()), "name": "Classes", "mastery_level": 0.1},
        {"concept_id": str(uuid4()), "name": "Error Handling", "mastery_level": 0.6},
    ]
}

SAMPLE_LLM_PLAN = {
    "weeks": [
        {
            "week_number": 1,
            "focus_areas": ["Loops", "Classes"],
            "lessons_to_complete": ["Intro to Loops", "Loop Patterns", "Class Basics"],
            "flashcard_sessions": 3,
            "quiz_practice": True,
            "estimated_hours": 8.0,
        },
        {
            "week_number": 2,
            "focus_areas": ["Functions", "Error Handling"],
            "lessons_to_complete": ["Function Design", "Error Handling Patterns"],
            "flashcard_sessions": 2,
            "quiz_practice": True,
            "estimated_hours": 6.0,
        },
        {
            "week_number": 3,
            "focus_areas": ["Variables"],
            "lessons_to_complete": ["Advanced Variables"],
            "flashcard_sessions": 1,
            "quiz_practice": False,
            "estimated_hours": 3.0,
        },
    ],
    "estimated_completion": "3 weeks",
    "total_estimated_hours": 17,
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
def mock_http_client():
    return AsyncMock()


@pytest.fixture
def study_plan_service(mock_llm, mock_http_client, settings):
    return StudyPlanService(llm=mock_llm, http_client=mock_http_client, settings=settings)


# --- Service-level tests ---


class TestStudyPlanService:
    async def test_generate_plan_success(self, study_plan_service, mock_llm, mock_http_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MASTERY_RESPONSE
        mock_http_client.get.return_value = mock_response

        mock_llm.generate.return_value = (json.dumps(SAMPLE_LLM_PLAN), 300, 600)

        result = await study_plan_service.generate_plan(
            user_id=uuid4(),
            course_id=uuid4(),
            available_hours_per_week=10,
            goal=None,
        )

        assert isinstance(result, StudyPlanResponse)
        assert len(result.weeks) == 3
        assert result.estimated_completion == "3 weeks"
        assert result.total_estimated_hours == 17
        assert result.model_used == "gemini-2.0-flash-lite"

    async def test_weak_concepts_prioritized_in_prompt(self, study_plan_service, mock_llm, mock_http_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MASTERY_RESPONSE
        mock_http_client.get.return_value = mock_response

        mock_llm.generate.return_value = (json.dumps(SAMPLE_LLM_PLAN), 300, 600)

        await study_plan_service.generate_plan(
            user_id=uuid4(),
            course_id=uuid4(),
            available_hours_per_week=10,
            goal="finish by end of month",
        )

        prompt = mock_llm.generate.call_args[0][0]
        assert "Loops" in prompt
        assert "Classes" in prompt
        assert "finish by end of month" in prompt

    async def test_calls_learning_service_with_correct_url(self, study_plan_service, mock_llm, mock_http_client, settings):
        course_id = uuid4()
        user_id = uuid4()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MASTERY_RESPONSE
        mock_http_client.get.return_value = mock_response

        mock_llm.generate.return_value = (json.dumps(SAMPLE_LLM_PLAN), 300, 600)

        await study_plan_service.generate_plan(
            user_id=user_id,
            course_id=course_id,
            available_hours_per_week=10,
            goal=None,
        )

        mock_http_client.get.assert_called_once()
        call_url = mock_http_client.get.call_args[0][0]
        assert str(course_id) in call_url
        assert "/concepts/mastery/course/" in call_url

    async def test_fallback_on_learning_service_unavailable(self, study_plan_service, mock_llm, mock_http_client):
        mock_http_client.get.side_effect = Exception("Connection refused")

        mock_llm.generate.return_value = (json.dumps(SAMPLE_LLM_PLAN), 300, 600)

        result = await study_plan_service.generate_plan(
            user_id=uuid4(),
            course_id=uuid4(),
            available_hours_per_week=10,
            goal=None,
        )

        assert isinstance(result, StudyPlanResponse)
        prompt = mock_llm.generate.call_args[0][0]
        assert "no mastery data available" in prompt.lower() or "general" in prompt.lower()

    async def test_gemini_failure_raises_502(self, study_plan_service, mock_llm, mock_http_client):
        from common.errors import AppError

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MASTERY_RESPONSE
        mock_http_client.get.return_value = mock_response

        mock_llm.generate.side_effect = AppError("LLM error", status_code=502)

        with pytest.raises(AppError) as exc_info:
            await study_plan_service.generate_plan(
                user_id=uuid4(),
                course_id=uuid4(),
                available_hours_per_week=10,
                goal=None,
            )
        assert exc_info.value.status_code == 502

    async def test_invalid_json_from_llm_raises_502(self, study_plan_service, mock_llm, mock_http_client):
        from common.errors import AppError

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MASTERY_RESPONSE
        mock_http_client.get.return_value = mock_response

        mock_llm.generate.return_value = ("not valid json", 300, 600)

        with pytest.raises(AppError) as exc_info:
            await study_plan_service.generate_plan(
                user_id=uuid4(),
                course_id=uuid4(),
                available_hours_per_week=10,
                goal=None,
            )
        assert exc_info.value.status_code == 502

    async def test_missing_weeks_key_raises_502(self, study_plan_service, mock_llm, mock_http_client):
        from common.errors import AppError

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MASTERY_RESPONSE
        mock_http_client.get.return_value = mock_response

        mock_llm.generate.return_value = ('{"no_weeks": []}', 300, 600)

        with pytest.raises(AppError) as exc_info:
            await study_plan_service.generate_plan(
                user_id=uuid4(),
                course_id=uuid4(),
                available_hours_per_week=10,
                goal=None,
            )
        assert exc_info.value.status_code == 502

    async def test_goal_included_in_prompt(self, study_plan_service, mock_llm, mock_http_client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MASTERY_RESPONSE
        mock_http_client.get.return_value = mock_response

        mock_llm.generate.return_value = (json.dumps(SAMPLE_LLM_PLAN), 300, 600)

        await study_plan_service.generate_plan(
            user_id=uuid4(),
            course_id=uuid4(),
            available_hours_per_week=15,
            goal="prepare for certification exam",
        )

        prompt = mock_llm.generate.call_args[0][0]
        assert "prepare for certification exam" in prompt
        assert "15" in prompt

    async def test_no_pii_in_prompt(self, study_plan_service, mock_llm, mock_http_client):
        """User IDs should not be sent to LLM."""
        user_id = uuid4()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MASTERY_RESPONSE
        mock_http_client.get.return_value = mock_response

        mock_llm.generate.return_value = (json.dumps(SAMPLE_LLM_PLAN), 300, 600)

        await study_plan_service.generate_plan(
            user_id=user_id,
            course_id=uuid4(),
            available_hours_per_week=10,
            goal=None,
        )

        prompt = mock_llm.generate.call_args[0][0]
        assert str(user_id) not in prompt


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
async def client(settings, mock_cache, mock_llm, mock_http_client):
    import app.main as main_module

    main_module.app_settings = settings
    main_module._ai_service = AIService(mock_llm, mock_cache, settings)
    main_module._tutor_service = main_module.TutorService(mock_llm, mock_cache, settings)
    main_module._credit_service = CreditService(cache=mock_cache)
    main_module._study_plan_service = StudyPlanService(
        llm=mock_llm, http_client=mock_http_client, settings=settings,
    )

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestStudyPlanRoute:
    async def test_requires_auth(self, client):
        resp = await client.post("/ai/study-plan", json={
            "course_id": str(uuid4()),
        })
        assert resp.status_code in (401, 422)

    async def test_any_authenticated_user_can_access(self, client, student_token, mock_llm, mock_cache, mock_http_client):
        mock_mastery = MagicMock()
        mock_mastery.status_code = 200
        mock_mastery.json.return_value = SAMPLE_MASTERY_RESPONSE
        mock_http_client.get.return_value = mock_mastery

        mock_llm.generate.return_value = (json.dumps(SAMPLE_LLM_PLAN), 300, 600)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/study-plan",
            json={"course_id": str(uuid4())},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "weeks" in data
        assert "estimated_completion" in data
        assert "total_estimated_hours" in data
        assert "model_used" in data

    async def test_credits_enforced(self, client, student_token, mock_cache):
        mock_cache.get_credits_used.return_value = 10  # free plan limit

        resp = await client.post(
            "/ai/study-plan",
            json={"course_id": str(uuid4())},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

    async def test_validates_hours_range(self, client, student_token):
        resp = await client.post(
            "/ai/study-plan",
            json={"course_id": str(uuid4()), "available_hours_per_week": 50},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 422

    async def test_validates_goal_max_length(self, client, student_token):
        resp = await client.post(
            "/ai/study-plan",
            json={"course_id": str(uuid4()), "goal": "x" * 501},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 422

    async def test_response_shape(self, client, student_token, mock_llm, mock_cache, mock_http_client):
        mock_mastery = MagicMock()
        mock_mastery.status_code = 200
        mock_mastery.json.return_value = SAMPLE_MASTERY_RESPONSE
        mock_http_client.get.return_value = mock_mastery

        mock_llm.generate.return_value = (json.dumps(SAMPLE_LLM_PLAN), 300, 600)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/study-plan",
            json={"course_id": str(uuid4()), "available_hours_per_week": 15, "goal": "pass exam"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        week = data["weeks"][0]
        assert "week_number" in week
        assert "focus_areas" in week
        assert "lessons_to_complete" in week
        assert "flashcard_sessions" in week
        assert "quiz_practice" in week
        assert "estimated_hours" in week
