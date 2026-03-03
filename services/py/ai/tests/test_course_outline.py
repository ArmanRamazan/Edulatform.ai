import json
from uuid import uuid4
from unittest.mock import AsyncMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from common.errors import AppError
from app.config import Settings
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient
from app.services.ai_service import AIService
from app.services.credit_service import CreditService


SAMPLE_OUTLINE = {
    "modules": [
        {
            "title": "Introduction to Python",
            "description": "Getting started with Python programming",
            "lessons": [
                {
                    "title": "Installing Python",
                    "description": "How to install Python on your machine",
                    "key_concepts": ["installation", "environment setup"],
                    "estimated_duration_minutes": 15,
                },
                {
                    "title": "Hello World",
                    "description": "Write your first Python program",
                    "key_concepts": ["print function", "syntax"],
                    "estimated_duration_minutes": 20,
                },
                {
                    "title": "Variables and Types",
                    "description": "Learn about Python data types",
                    "key_concepts": ["int", "str", "float", "bool"],
                    "estimated_duration_minutes": 30,
                },
            ],
        },
        {
            "title": "Control Flow",
            "description": "Conditionals and loops in Python",
            "lessons": [
                {
                    "title": "If Statements",
                    "description": "Conditional logic in Python",
                    "key_concepts": ["if", "elif", "else"],
                    "estimated_duration_minutes": 25,
                },
                {
                    "title": "Loops",
                    "description": "For and while loops",
                    "key_concepts": ["for loop", "while loop", "break", "continue"],
                    "estimated_duration_minutes": 30,
                },
                {
                    "title": "List Comprehensions",
                    "description": "Pythonic way to create lists",
                    "key_concepts": ["comprehension syntax", "filtering"],
                    "estimated_duration_minutes": 25,
                },
            ],
        },
    ]
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


class TestGenerateOutlineService:
    async def test_success(self, ai_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_OUTLINE), 200, 500)

        result = await ai_service.generate_outline(
            topic="Python Programming",
            level="beginner",
            target_audience="Complete beginners",
            num_modules=2,
        )

        assert len(result.modules) == 2
        assert result.modules[0].title == "Introduction to Python"
        assert len(result.modules[0].lessons) == 3
        assert result.modules[0].lessons[0].key_concepts == ["installation", "environment setup"]
        assert result.total_lessons == 6
        assert result.estimated_duration_hours > 0
        assert result.model_used == "gemini-2.0-flash-lite"
        mock_llm.generate.assert_called_once()

    async def test_prompt_contains_params(self, ai_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_OUTLINE), 200, 500)

        await ai_service.generate_outline(
            topic="Machine Learning",
            level="advanced",
            target_audience="Data scientists",
            num_modules=3,
        )

        prompt = mock_llm.generate.call_args[0][0]
        assert "Machine Learning" in prompt
        assert "advanced" in prompt
        assert "Data scientists" in prompt
        assert "3" in prompt

    async def test_strips_markdown_fences(self, ai_service, mock_llm):
        wrapped = f"```json\n{json.dumps(SAMPLE_OUTLINE)}\n```"
        mock_llm.generate.return_value = (wrapped, 200, 500)

        result = await ai_service.generate_outline(
            topic="Python", level="beginner", target_audience="Students", num_modules=2,
        )

        assert len(result.modules) == 2

    async def test_invalid_json_raises_502(self, ai_service, mock_llm):
        mock_llm.generate.return_value = ("not valid json at all", 200, 500)

        with pytest.raises(AppError) as exc_info:
            await ai_service.generate_outline(
                topic="Python", level="beginner", target_audience="Students", num_modules=2,
            )
        assert exc_info.value.status_code == 502

    async def test_missing_modules_key_raises_502(self, ai_service, mock_llm):
        mock_llm.generate.return_value = ('{"wrong_key": []}', 200, 500)

        with pytest.raises(AppError) as exc_info:
            await ai_service.generate_outline(
                topic="Python", level="beginner", target_audience="Students", num_modules=2,
            )
        assert exc_info.value.status_code == 502

    async def test_calculates_duration_hours(self, ai_service, mock_llm):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_OUTLINE), 200, 500)

        result = await ai_service.generate_outline(
            topic="Python", level="beginner", target_audience="Students", num_modules=2,
        )

        # 15+20+30+25+30+25 = 145 min -> round(145/60) = 2 hours
        assert result.estimated_duration_hours == 2


# --- Route-level tests ---


class TestCourseOutlineRoute:
    async def test_requires_auth(self, client):
        resp = await client.post("/ai/course/outline", json={
            "topic": "Python", "level": "beginner",
            "target_audience": "Students", "num_modules": 5,
        })
        assert resp.status_code == 422

    async def test_student_forbidden(self, client, student_token):
        resp = await client.post(
            "/ai/course/outline",
            json={"topic": "Python", "level": "beginner", "target_audience": "Students", "num_modules": 5},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

    async def test_teacher_can_generate(self, client, teacher_token, mock_llm, mock_cache):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_OUTLINE), 200, 500)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/course/outline",
            json={"topic": "Python", "level": "beginner", "target_audience": "Students", "num_modules": 2},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["modules"]) == 2
        assert data["total_lessons"] == 6

    async def test_admin_can_generate(self, client, admin_token, mock_llm, mock_cache):
        mock_llm.generate.return_value = (json.dumps(SAMPLE_OUTLINE), 200, 500)
        mock_cache.increment_credits.return_value = 1
        mock_cache.get_credits_used.return_value = 0

        resp = await client.post(
            "/ai/course/outline",
            json={"topic": "Python", "level": "beginner", "target_audience": "Students", "num_modules": 2},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    async def test_credits_enforced(self, client, teacher_token, mock_cache):
        mock_cache.get_credits_used.return_value = 10  # free plan limit

        resp = await client.post(
            "/ai/course/outline",
            json={"topic": "Python", "level": "beginner", "target_audience": "Students", "num_modules": 2},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 403

    async def test_validates_level(self, client, teacher_token):
        resp = await client.post(
            "/ai/course/outline",
            json={"topic": "Python", "level": "expert", "target_audience": "Students", "num_modules": 2},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 422

    async def test_validates_num_modules_range(self, client, teacher_token):
        resp = await client.post(
            "/ai/course/outline",
            json={"topic": "Python", "level": "beginner", "target_audience": "Students", "num_modules": 20},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 422
