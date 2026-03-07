from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

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
from app.services.designer_service import DesignerService
from app.services.orchestrator_service import AgentOrchestrator
from app.services.strategist_service import StrategistService


@pytest.fixture
def mock_strategist():
    return AsyncMock(spec=StrategistService)


@pytest.fixture
def mock_designer():
    return AsyncMock(spec=DesignerService)


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def orchestrator(mock_strategist, mock_designer, mock_cache, mock_http_client, settings):
    return AgentOrchestrator(
        strategist=mock_strategist,
        designer=mock_designer,
        cache=mock_cache,
        http_client=mock_http_client,
        settings=settings,
    )


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def sample_concept():
    return PathConcept(
        concept_id=uuid4(),
        name="Python Decorators",
        priority=1,
        estimated_sessions=3,
        prerequisites=[],
        mastery=0.2,
    )


@pytest.fixture
def sample_mission(sample_concept):
    return MissionBlueprint(
        concept_name=sample_concept.name,
        concept_id=sample_concept.concept_id,
        recap_questions=[
            RecapQuestion(
                question="What is a closure?",
                expected_answer="A function that captures variables from enclosing scope",
                concept_ref="closures",
            ),
        ],
        reading_content="Decorators are functions that modify other functions...",
        check_questions=[
            CheckQuestion(
                question="What does @decorator syntax do?",
                options=["Calls", "Wraps", "Deletes", "Imports"],
                correct_index=1,
                explanation="@ syntax applies the decorator",
            ),
        ],
        code_case=CodeCase(
            code_snippet="def timer(func): ...",
            language="python",
            question="What happens if...",
            expected_answer="It wraps the function",
            source_path="examples/decorators.py",
        ),
    )


@pytest.fixture
def sample_session_result():
    return SessionResult(
        session_id="session-123",
        score=75.0,
        mastery_delta=0.15,
        duration_seconds=600,
        strengths=["understood closures"],
        gaps=["needs practice with decorators"],
    )


class TestGetDailyMission:
    async def test_returns_cached_mission_if_exists(
        self, orchestrator, mock_cache, user_id, org_id, sample_mission
    ):
        today = date.today().isoformat()
        cache_key = f"ai:daily:{user_id}:{today}"
        mock_cache._redis = AsyncMock()
        mock_cache._get = AsyncMock(return_value=_serialize_mission(sample_mission))

        result = await orchestrator.get_daily_mission(user_id, org_id)

        assert result.concept_name == sample_mission.concept_name
        assert result.concept_id == sample_mission.concept_id

    async def test_does_not_call_strategist_when_cached(
        self, orchestrator, mock_strategist, mock_cache, user_id, org_id, sample_mission
    ):
        mock_cache._get = AsyncMock(return_value=_serialize_mission(sample_mission))

        await orchestrator.get_daily_mission(user_id, org_id)

        mock_strategist.get_next_concept.assert_not_called()

    async def test_calls_strategist_then_designer_when_no_cache(
        self, orchestrator, mock_strategist, mock_designer, mock_cache, user_id, org_id, sample_concept, sample_mission
    ):
        mock_cache._get = AsyncMock(return_value=None)
        mock_cache._set = AsyncMock()
        mock_strategist.get_next_concept.return_value = sample_concept
        mock_designer.design_mission.return_value = sample_mission

        result = await orchestrator.get_daily_mission(user_id, org_id)

        mock_strategist.get_next_concept.assert_called_once_with(user_id, org_id)
        mock_designer.design_mission.assert_called_once()
        assert result.concept_name == sample_mission.concept_name

    async def test_passes_previous_concepts_to_designer(
        self, orchestrator, mock_strategist, mock_designer, mock_cache, user_id, org_id, sample_concept, sample_mission
    ):
        mock_cache._get = AsyncMock(side_effect=[None, json.dumps(["closures", "functions", "scope"])])
        mock_cache._set = AsyncMock()
        mock_strategist.get_next_concept.return_value = sample_concept
        mock_designer.design_mission.return_value = sample_mission

        await orchestrator.get_daily_mission(user_id, org_id)

        call_kwargs = mock_designer.design_mission.call_args
        assert call_kwargs[1]["previous_concepts"] == ["closures", "functions", "scope"]

    async def test_caches_mission_after_generation(
        self, orchestrator, mock_strategist, mock_designer, mock_cache, user_id, org_id, sample_concept, sample_mission
    ):
        mock_cache._get = AsyncMock(side_effect=[None, None])
        mock_cache._set = AsyncMock()
        mock_strategist.get_next_concept.return_value = sample_concept
        mock_designer.design_mission.return_value = sample_mission

        await orchestrator.get_daily_mission(user_id, org_id)

        today = date.today().isoformat()
        cache_key = f"ai:daily:{user_id}:{today}"
        mock_cache._set.assert_called_once()
        args = mock_cache._set.call_args[0]
        assert args[0] == cache_key

    async def test_raises_when_no_concept_available(
        self, orchestrator, mock_strategist, mock_cache, user_id, org_id
    ):
        mock_cache._get = AsyncMock(return_value=None)
        mock_strategist.get_next_concept.return_value = None

        with pytest.raises(Exception, match="No concept available"):
            await orchestrator.get_daily_mission(user_id, org_id)

    async def test_limits_previous_concepts_to_last_3(
        self, orchestrator, mock_strategist, mock_designer, mock_cache, user_id, org_id, sample_concept, sample_mission
    ):
        completed = ["c1", "c2", "c3", "c4", "c5"]
        mock_cache._get = AsyncMock(side_effect=[None, json.dumps(completed)])
        mock_cache._set = AsyncMock()
        mock_strategist.get_next_concept.return_value = sample_concept
        mock_designer.design_mission.return_value = sample_mission

        await orchestrator.get_daily_mission(user_id, org_id)

        call_kwargs = mock_designer.design_mission.call_args
        assert call_kwargs[1]["previous_concepts"] == ["c3", "c4", "c5"]

    async def test_accepts_mastery_data_from_learning(
        self, orchestrator, mock_strategist, mock_designer, mock_cache, user_id, org_id, sample_concept, sample_mission
    ):
        """Learning pushes mastery data — orchestrator must accept and forward it."""
        mastery_data = [
            {"concept_id": str(sample_concept.concept_id), "mastery": 0.4},
        ]
        mock_cache._get = AsyncMock(side_effect=[None, None])
        mock_cache._set = AsyncMock()
        mock_strategist.get_next_concept.return_value = sample_concept
        mock_designer.design_mission.return_value = sample_mission

        # Must accept mastery_data kwarg without TypeError
        result = await orchestrator.get_daily_mission(user_id, org_id, mastery_data=mastery_data)

        assert result.concept_name == sample_mission.concept_name


class TestCompleteSession:
    async def test_adapts_path_via_strategist(
        self, orchestrator, mock_strategist, mock_cache, user_id, org_id, sample_session_result
    ):
        mock_cache._get = AsyncMock(return_value=None)
        mock_cache._set = AsyncMock()
        mock_strategist.adapt_path.return_value = AsyncMock()
        mock_strategist.get_next_concept.return_value = PathConcept(
            concept_id=uuid4(), name="Next Topic", priority=1,
            estimated_sessions=2, prerequisites=[], mastery=0.1,
        )

        await orchestrator.complete_session(
            user_id=user_id,
            org_id=org_id,
            session_result=sample_session_result,
            concept_id=uuid4(),
        )

        mock_strategist.adapt_path.assert_called_once()

    async def test_does_not_call_learning_service_for_mastery_update(
        self, orchestrator, mock_strategist, mock_cache, mock_http_client, user_id, org_id, sample_session_result
    ):
        """AI must NOT call Learning's PATCH /concepts/mastery — Learning owns its own mastery."""
        mock_cache._get = AsyncMock(return_value=None)
        mock_cache._set = AsyncMock()
        mock_strategist.adapt_path.return_value = AsyncMock()
        mock_strategist.get_next_concept.return_value = None

        await orchestrator.complete_session(
            user_id=user_id,
            org_id=org_id,
            session_result=sample_session_result,
            concept_id=uuid4(),
        )

        mock_http_client.patch.assert_not_called()

    async def test_records_completed_concept_in_cache(
        self, orchestrator, mock_strategist, mock_cache, user_id, org_id, sample_session_result
    ):
        mock_cache._get = AsyncMock(return_value=json.dumps(["prev_concept"]))
        mock_cache._set = AsyncMock()
        mock_strategist.adapt_path.return_value = AsyncMock()
        mock_strategist.get_next_concept.return_value = None

        await orchestrator.complete_session(
            user_id=user_id,
            org_id=org_id,
            session_result=sample_session_result,
            concept_id=uuid4(),
        )

        # Verify completed concepts cache was updated
        set_calls = mock_cache._set.call_args_list
        completed_call = [c for c in set_calls if "ai:completed:" in c[0][0]]
        assert len(completed_call) == 1

    async def test_returns_summary_with_next_concept_preview(
        self, orchestrator, mock_strategist, mock_cache, user_id, org_id, sample_session_result
    ):
        next_concept = PathConcept(
            concept_id=uuid4(), name="Async Python", priority=1,
            estimated_sessions=2, prerequisites=[], mastery=0.1,
        )
        mock_cache._get = AsyncMock(return_value=None)
        mock_cache._set = AsyncMock()
        mock_strategist.adapt_path.return_value = AsyncMock()
        mock_strategist.get_next_concept.return_value = next_concept

        result = await orchestrator.complete_session(
            user_id=user_id,
            org_id=org_id,
            session_result=sample_session_result,
            concept_id=uuid4(),
        )

        assert result["next_concept_preview"] == "Async Python"

    async def test_returns_none_preview_when_path_complete(
        self, orchestrator, mock_strategist, mock_cache, user_id, org_id, sample_session_result
    ):
        mock_cache._get = AsyncMock(return_value=None)
        mock_cache._set = AsyncMock()
        mock_strategist.adapt_path.return_value = AsyncMock()
        mock_strategist.get_next_concept.return_value = None

        result = await orchestrator.complete_session(
            user_id=user_id,
            org_id=org_id,
            session_result=sample_session_result,
            concept_id=uuid4(),
        )

        assert result["next_concept_preview"] is None

    async def test_returns_total_completed_count(
        self, orchestrator, mock_strategist, mock_cache, user_id, org_id, sample_session_result
    ):
        existing = ["concept_a", "concept_b"]
        mock_cache._get = AsyncMock(return_value=json.dumps(existing))
        mock_cache._set = AsyncMock()
        mock_strategist.adapt_path.return_value = AsyncMock()
        mock_strategist.get_next_concept.return_value = None

        result = await orchestrator.complete_session(
            user_id=user_id,
            org_id=org_id,
            session_result=sample_session_result,
            concept_id=uuid4(),
        )

        assert result["total_completed"] == 3  # 2 existing + 1 new


def _serialize_mission(mission: MissionBlueprint) -> str:
    return json.dumps({
        "concept_name": mission.concept_name,
        "concept_id": str(mission.concept_id),
        "recap_questions": [
            {"question": q.question, "expected_answer": q.expected_answer, "concept_ref": q.concept_ref}
            for q in mission.recap_questions
        ],
        "reading_content": mission.reading_content,
        "check_questions": [
            {
                "question": q.question,
                "options": q.options,
                "correct_index": q.correct_index,
                "explanation": q.explanation,
            }
            for q in mission.check_questions
        ],
        "code_case": {
            "code_snippet": mission.code_case.code_snippet,
            "language": mission.code_case.language,
            "question": mission.code_case.question,
            "expected_answer": mission.code_case.expected_answer,
            "source_path": mission.code_case.source_path,
        } if mission.code_case else None,
    })
