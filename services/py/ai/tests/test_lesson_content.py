import json
from uuid import uuid4
from unittest.mock import AsyncMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient
from app.services.ai_service import AIService
from app.services.credit_service import CreditService


SAMPLE_LESSON_RESPONSE = {
    "content": "## Introduction\n\nThis lesson covers Python basics.\n\n## Main Content\n\n### Variables\n\nVariables store data.\n\n## Key Takeaways\n\n- Python is simple\n- Variables are fundamental\n\n## Practice Exercises\n\n1. Create a variable\n2. Print its value",
    "key_concepts": ["variables", "data types", "print function"],
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
def ai_service(mock_llm, mock_cache, settings):
    return AIService(llm=mock_llm, cache=mock_cache, settings=settings)


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
    return _make_token(settings, role="admin", tier="pro")


@pytest.fixture
async def client(settings, mock_cache, mock_llm):
    import app.main as main_module

    main_module.app_settings = settings
    main_module._ai_service = AIService(mock_llm, mock_cache, settings)
    main_module._tutor_service = main_module.TutorService(mock_llm, mock_cache, settings)
    main_module._credit_service = CreditService(cache=mock_cache)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# --- Service-level tests ---


class TestGenerateLessonContentService:
    async def test_success_article_format(self, ai_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_LESSON_RESPONSE), 200, 500)

        result = await ai_service.generate_lesson_content(
            title="Python Basics",
            description="Learn the fundamentals of Python",
            course_context="Introduction to Programming",
            format="article",
        )

        assert result.content == SAMPLE_LESSON_RESPONSE["content"]
        assert result.key_concepts == ["variables", "data types", "print function"]
        assert result.estimated_duration_minutes > 0
        assert result.model_used == "gemini-2.0-flash-lite"
        mock_llm.generate.assert_called_once()

    async def test_success_tutorial_format(self, ai_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_LESSON_RESPONSE), 200, 500)

        result = await ai_service.generate_lesson_content(
            title="Build a Calculator",
            description="Step-by-step guide",
            course_context="Python Projects",
            format="tutorial",
        )

        assert result.content == SAMPLE_LESSON_RESPONSE["content"]
        assert result.model_used == "gemini-2.0-flash-lite"

    async def test_prompt_contains_params_article(self, ai_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_LESSON_RESPONSE), 200, 500)

        await ai_service.generate_lesson_content(
            title="Machine Learning Intro",
            description="Overview of ML concepts",
            course_context="Data Science 101",
            format="article",
        )

        prompt = mock_llm.generate.call_args[0][0]
        assert "Machine Learning Intro" in prompt
        assert "Overview of ML concepts" in prompt
        assert "Data Science 101" in prompt

    async def test_prompt_contains_params_tutorial(self, ai_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_LESSON_RESPONSE), 200, 500)

        await ai_service.generate_lesson_content(
            title="Build a REST API",
            description="Hands-on tutorial",
            course_context="Web Development",
            format="tutorial",
        )

        prompt = mock_llm.generate.call_args[0][0]
        assert "Build a REST API" in prompt
        assert "step-by-step" in prompt.lower() or "Step" in prompt

    async def test_strips_markdown_fences(self, ai_service, mock_llm):
        wrapped = f"```json\n{json.dumps(SAMPLE_LESSON_RESPONSE)}\n```"
        mock_llm.generate.return_value = (wrapped, 200, 500)

        result = await ai_service.generate_lesson_content(
            title="Python", description=None, course_context=None, format="article",
        )

        assert result.content == SAMPLE_LESSON_RESPONSE["content"]

    async def test_invalid_json_raises_502(self, ai_service, mock_llm):
        from common.errors import AppError

        mock_llm.generate.return_value = ("not valid json", 200, 500)

        with pytest.raises(AppError) as exc_info:
            await ai_service.generate_lesson_content(
                title="Python", description=None, course_context=None, format="article",
            )
        assert exc_info.value.status_code == 502

    async def test_missing_content_key_raises_502(self, ai_service, mock_llm):
        from common.errors import AppError

        mock_llm.generate.return_value = ('{"wrong_key": "value"}', 200, 500)

        with pytest.raises(AppError) as exc_info:
            await ai_service.generate_lesson_content(
                title="Python", description=None, course_context=None, format="article",
            )
        assert exc_info.value.status_code == 502

    async def test_estimates_duration_by_word_count(self, ai_service, mock_llm):
        # ~200 words per minute reading speed
        # 400 words -> 2 minutes
        content_400_words = " ".join(["word"] * 400)
        response = {
            "content": content_400_words,
            "key_concepts": ["test"],
        }
        mock_llm.generate.return_value = (json.dumps(response), 200, 500)

        result = await ai_service.generate_lesson_content(
            title="Python", description=None, course_context=None, format="article",
        )

        assert result.estimated_duration_minutes == 2

    async def test_minimum_duration_is_one_minute(self, ai_service, mock_llm):
        response = {
            "content": "Short.",
            "key_concepts": ["brevity"],
        }
        mock_llm.generate.return_value = (json.dumps(response), 200, 500)

        result = await ai_service.generate_lesson_content(
            title="Python", description=None, course_context=None, format="article",
        )

        assert result.estimated_duration_minutes >= 1


# --- Route-level tests ---


class TestLessonContentRoute:
    async def test_requires_auth(self, client):
        resp = await client.post("/ai/lesson/generate", json={
            "title": "Python Basics",
        })
        assert resp.status_code == 422

    async def test_student_forbidden(self, client, student_token):
        resp = await client.post(
            "/ai/lesson/generate",
            json={"title": "Python Basics"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

    async def test_teacher_can_generate(self, client, teacher_token, mock_llm, mock_cache):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_LESSON_RESPONSE), 200, 500)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/lesson/generate",
            json={"title": "Python Basics"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data
        assert "key_concepts" in data
        assert "estimated_duration_minutes" in data
        assert "model_used" in data

    async def test_admin_can_generate(self, client, admin_token, mock_llm, mock_cache):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_LESSON_RESPONSE), 200, 500)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/lesson/generate",
            json={"title": "Python Basics"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    async def test_credits_enforced(self, client, teacher_token, mock_cache):
        mock_cache.get_credits_used.return_value = 10  # free plan limit

        resp = await client.post(
            "/ai/lesson/generate",
            json={"title": "Python Basics"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 403

    async def test_validates_title_max_length(self, client, teacher_token):
        resp = await client.post(
            "/ai/lesson/generate",
            json={"title": "x" * 201},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 422

    async def test_validates_format(self, client, teacher_token):
        resp = await client.post(
            "/ai/lesson/generate",
            json={"title": "Python Basics", "format": "invalid_format"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 422

    async def test_default_format_is_article(self, client, teacher_token, mock_llm, mock_cache):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_LESSON_RESPONSE), 200, 500)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/lesson/generate",
            json={"title": "Python Basics"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        # Verify article prompt was used
        prompt = mock_llm.generate.call_args[0][0]
        assert "comprehensive educational lesson" in prompt.lower() or "Introduction" in prompt

    async def test_tutorial_format(self, client, teacher_token, mock_llm, mock_cache):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_LESSON_RESPONSE), 200, 500)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/lesson/generate",
            json={"title": "Build a Calculator", "format": "tutorial"},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
