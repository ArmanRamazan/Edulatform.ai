from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.domain.agent import PathConcept
from app.domain.coach import SessionResult
from app.domain.mission import (
    CheckQuestion,
    CodeCase,
    MissionBlueprint,
    RecapQuestion,
)
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient
from app.services.orchestrator_service import AgentOrchestrator


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def mock_llm():
    mock = AsyncMock(spec=GeminiClient)
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


def _make_token(settings: Settings, user_id: str | None = None, tier: str = "free") -> str:
    payload = {
        "sub": user_id or str(uuid4()),
        "role": "student",
        "subscription_tier": tier,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
def sample_mission():
    return MissionBlueprint(
        concept_name="Python Decorators",
        concept_id=uuid4(),
        recap_questions=[
            RecapQuestion(question="What is a closure?", expected_answer="captures vars", concept_ref="closures"),
        ],
        reading_content="Decorators wrap functions...",
        check_questions=[
            CheckQuestion(
                question="What does @ do?",
                options=["Call", "Wrap", "Delete", "Import"],
                correct_index=1,
                explanation="Applies decorator",
            ),
        ],
        code_case=CodeCase(
            code_snippet="def timer(f): ...",
            language="python",
            question="What happens?",
            expected_answer="Wraps",
            source_path="ex.py",
        ),
    )


@pytest.fixture
def mock_orchestrator(sample_mission):
    orch = AsyncMock(spec=AgentOrchestrator)
    orch.get_daily_mission.return_value = sample_mission
    orch.complete_session.return_value = {
        "next_concept_preview": "Async Python",
        "total_completed": 5,
        "score": 85.0,
        "mastery_delta": 0.2,
    }
    return orch


@pytest.fixture
def mock_coach():
    from app.services.coach_service import CoachService
    mock = AsyncMock(spec=CoachService)
    mock.end_session.return_value = SessionResult(
        session_id="session-abc",
        score=85.0,
        mastery_delta=0.2,
        duration_seconds=600,
        strengths=["good understanding"],
        gaps=["needs practice"],
    )
    return mock


@pytest.fixture
async def client(settings, mock_cache, mock_llm, mock_orchestrator, mock_coach):
    import app.main as main_module

    main_module.app_settings = settings
    main_module._credit_service = main_module.CreditService(cache=mock_cache)
    main_module._orchestrator_service = mock_orchestrator
    main_module._coach_service = mock_coach

    # Also set required services to avoid assertion errors
    main_module._ai_service = main_module.AIService(mock_llm, mock_cache, settings)
    main_module._tutor_service = main_module.TutorService(mock_llm, mock_cache, settings)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestDailyMission:
    async def test_returns_mission_for_authenticated_user(
        self, client, settings, mock_orchestrator, sample_mission, mock_cache
    ):
        mock_cache.get_credits_used.return_value = 0
        mock_cache.increment_credits.return_value = 1
        token = _make_token(settings)
        org_id = str(uuid4())

        resp = await client.post(
            "/ai/mission/daily",
            json={"org_id": org_id, "mastery": []},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["concept_name"] == "Python Decorators"
        assert "check_questions" in data

    async def test_returns_401_without_auth(self, client):
        resp = await client.post(
            "/ai/mission/daily",
            json={"org_id": str(uuid4()), "mastery": []},
        )
        assert resp.status_code in (401, 422)

    async def test_calls_orchestrator_with_user_and_org(
        self, client, settings, mock_orchestrator, mock_cache
    ):
        mock_cache.get_credits_used.return_value = 0
        mock_cache.increment_credits.return_value = 1
        user_id = str(uuid4())
        org_id = str(uuid4())
        token = _make_token(settings, user_id=user_id)

        await client.post(
            "/ai/mission/daily",
            json={"org_id": org_id, "mastery": []},
            headers={"Authorization": f"Bearer {token}"},
        )

        mock_orchestrator.get_daily_mission.assert_called_once()

    async def test_403_when_credits_exhausted(self, client, settings, mock_cache):
        mock_cache.get_credits_used.return_value = 10
        token = _make_token(settings, tier="free")

        resp = await client.post(
            "/ai/mission/daily",
            json={"org_id": str(uuid4()), "mastery": []},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403

    async def test_forwards_mastery_data_to_orchestrator(
        self, client, settings, mock_orchestrator, mock_cache
    ):
        """Mastery pushed by Learning must be forwarded to orchestrator."""
        mock_cache.get_credits_used.return_value = 0
        mock_cache.increment_credits.return_value = 1
        concept_id = str(uuid4())
        token = _make_token(settings)

        await client.post(
            "/ai/mission/daily",
            json={
                "org_id": str(uuid4()),
                "mastery": [{"concept_id": concept_id, "mastery": 0.5}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        call_kwargs = mock_orchestrator.get_daily_mission.call_args
        assert "mastery_data" in call_kwargs[1]
        assert len(call_kwargs[1]["mastery_data"]) == 1
        assert call_kwargs[1]["mastery_data"][0]["mastery"] == 0.5


class TestMissionComplete:
    async def test_returns_completion_summary(
        self, client, settings, mock_orchestrator, mock_cache
    ):
        token = _make_token(settings)

        resp = await client.post(
            "/ai/mission/complete",
            json={
                "session_id": "session-abc",
                "concept_id": str(uuid4()),
                "org_id": str(uuid4()),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["next_concept_preview"] == "Async Python"
        assert data["total_completed"] == 5
        assert data["score"] == 85.0

    async def test_returns_401_without_auth(self, client):
        resp = await client.post(
            "/ai/mission/complete",
            json={"session_id": "test", "concept_id": str(uuid4()), "org_id": str(uuid4())},
        )
        assert resp.status_code in (401, 422)
