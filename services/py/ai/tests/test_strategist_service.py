from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

from app.config import Settings
from app.domain.agent import LearningPath, PathConcept
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient
from app.services.strategist_service import StrategistService


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def concept_ids():
    return [uuid4() for _ in range(4)]


@pytest.fixture
def rag_concepts(concept_ids):
    return [
        {"id": str(concept_ids[0]), "name": "Python Basics", "description": "Fundamentals"},
        {"id": str(concept_ids[1]), "name": "OOP", "description": "Object-oriented programming"},
        {"id": str(concept_ids[2]), "name": "Decorators", "description": "Advanced decorators"},
        {"id": str(concept_ids[3]), "name": "Testing", "description": "Unit testing"},
    ]


@pytest.fixture
def mastery_data(concept_ids):
    return {
        "items": [
            {"concept_id": str(concept_ids[0]), "concept_name": "Python Basics", "mastery": 0.8},
            {"concept_id": str(concept_ids[1]), "concept_name": "OOP", "mastery": 0.3},
            {"concept_id": str(concept_ids[2]), "concept_name": "Decorators", "mastery": 0.1},
            {"concept_id": str(concept_ids[3]), "concept_name": "Testing", "mastery": 0.6},
        ]
    }


@pytest.fixture
def llm_path_response(concept_ids):
    return json.dumps([
        {
            "concept_id": str(concept_ids[1]),
            "name": "OOP",
            "priority": 1,
            "estimated_sessions": 3,
            "prerequisites": [str(concept_ids[0])],
        },
        {
            "concept_id": str(concept_ids[2]),
            "name": "Decorators",
            "priority": 2,
            "estimated_sessions": 2,
            "prerequisites": [str(concept_ids[1])],
        },
        {
            "concept_id": str(concept_ids[3]),
            "name": "Testing",
            "priority": 1,
            "estimated_sessions": 2,
            "prerequisites": [],
        },
        {
            "concept_id": str(concept_ids[0]),
            "name": "Python Basics",
            "priority": 3,
            "estimated_sessions": 1,
            "prerequisites": [],
        },
    ])


@pytest.fixture
def mock_llm():
    mock = AsyncMock(spec=GeminiClient)
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def mock_http():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def service(mock_llm, mock_cache, mock_http, settings):
    return StrategistService(
        gemini_client=mock_llm,
        cache=mock_cache,
        http_client=mock_http,
        settings=settings,
    )


# --- plan_path tests ---


async def test_plan_path_returns_learning_path(
    service, mock_llm, mock_cache, mock_http,
    user_id, org_id, concept_ids, rag_concepts, llm_path_response,
):
    rag_resp = MagicMock()
    rag_resp.status_code = 200
    rag_resp.json.return_value = rag_concepts

    mock_http.get.side_effect = [rag_resp]
    mock_llm.generate.return_value = (llm_path_response, 500, 300)
    mock_cache.get_path.return_value = None

    result = await service.plan_path(user_id, org_id, {"role": "backend developer"})

    assert isinstance(result, LearningPath)
    assert result.user_id == user_id
    assert result.organization_id == org_id
    assert len(result.concepts_ordered) == 4
    assert result.current_index == 0


async def test_plan_path_merges_mastery(
    service, mock_llm, mock_cache, mock_http,
    user_id, org_id, concept_ids, rag_concepts, mastery_data, llm_path_response,
):
    """Mastery is passed as parameter (push model) and merged into path concepts."""
    rag_resp = MagicMock()
    rag_resp.status_code = 200
    rag_resp.json.return_value = rag_concepts

    mock_http.get.side_effect = [rag_resp]
    mock_llm.generate.return_value = (llm_path_response, 500, 300)
    mock_cache.get_path.return_value = None

    # Mastery is pushed by Learning in the request — not fetched via HTTP
    result = await service.plan_path(
        user_id, org_id, {"role": "backend developer"}, mastery=mastery_data["items"]
    )

    oop_concept = next(c for c in result.concepts_ordered if c.name == "OOP")
    assert oop_concept.mastery == 0.3

    basics_concept = next(c for c in result.concepts_ordered if c.name == "Python Basics")
    assert basics_concept.mastery == 0.8


async def test_plan_path_caches_result(
    service, mock_llm, mock_cache, mock_http,
    user_id, org_id, rag_concepts, llm_path_response,
):
    rag_resp = MagicMock()
    rag_resp.status_code = 200
    rag_resp.json.return_value = rag_concepts

    mock_http.get.side_effect = [rag_resp]
    mock_llm.generate.return_value = (llm_path_response, 500, 300)
    mock_cache.get_path.return_value = None

    await service.plan_path(user_id, org_id, {"role": "dev"})

    mock_cache.set_path.assert_called_once()
    call_args = mock_cache.set_path.call_args
    assert str(user_id) in call_args[0][0]


async def test_plan_path_graceful_on_rag_failure(
    service, mock_llm, mock_cache, mock_http,
    user_id, org_id, mastery_data, llm_path_response,
):
    mock_http.get.side_effect = httpx.ConnectError("connection refused")
    mock_cache.get_path.return_value = None

    result = await service.plan_path(user_id, org_id, {"role": "dev"})

    assert result.concepts_ordered == []


async def test_plan_path_no_pii_in_prompt(
    service, mock_llm, mock_cache, mock_http,
    user_id, org_id, rag_concepts, llm_path_response,
):
    rag_resp = MagicMock()
    rag_resp.status_code = 200
    rag_resp.json.return_value = rag_concepts

    mock_http.get.side_effect = [rag_resp]
    mock_llm.generate.return_value = (llm_path_response, 500, 300)
    mock_cache.get_path.return_value = None

    await service.plan_path(user_id, org_id, {"role": "dev"})

    prompt = mock_llm.generate.call_args[0][0]
    assert str(user_id) not in prompt


async def test_plan_path_uses_provided_mastery_without_http_call(
    service, mock_llm, mock_cache, mock_http,
    user_id, org_id, concept_ids, rag_concepts, mastery_data, llm_path_response,
):
    """When mastery is provided by Learning, strategist must NOT call Learning over HTTP."""
    rag_resp = MagicMock()
    rag_resp.status_code = 200
    rag_resp.json.return_value = rag_concepts

    # Only RAG call allowed — no Learning mastery HTTP call
    mock_http.get.side_effect = [rag_resp]
    mock_llm.generate.return_value = (llm_path_response, 500, 300)
    mock_cache.get_path.return_value = None

    provided_mastery = mastery_data["items"]

    result = await service.plan_path(
        user_id, org_id, {"role": "backend developer"}, mastery=provided_mastery
    )

    assert isinstance(result, LearningPath)
    # Exactly one HTTP call (RAG), not two (RAG + Learning)
    assert mock_http.get.call_count == 1

    # Mastery values from provided data are reflected
    oop_concept = next(c for c in result.concepts_ordered if c.name == "OOP")
    assert oop_concept.mastery == 0.3


async def test_plan_path_never_calls_learning_service_for_mastery(
    service, mock_llm, mock_cache, mock_http,
    user_id, org_id, rag_concepts, llm_path_response,
):
    """plan_path() must NEVER call Learning mastery endpoint — even when mastery not provided.

    The push model requires Learning to include mastery in the request body.
    AI must not make callback HTTP calls to Learning for mastery data.
    """
    rag_resp = MagicMock()
    rag_resp.status_code = 200
    rag_resp.json.return_value = rag_concepts

    # Only one GET response available — RAG only. Any second call would exhaust
    # the side_effect list, causing StopAsyncIteration and failing the test.
    mock_http.get.side_effect = [rag_resp]
    mock_llm.generate.return_value = (llm_path_response, 500, 300)
    mock_cache.get_path.return_value = None

    # No mastery parameter — strategist must not fetch it from Learning
    result = await service.plan_path(user_id, org_id, {"role": "dev"})

    assert isinstance(result, LearningPath)
    assert mock_http.get.call_count == 1  # only RAG, never Learning


# --- get_next_concept tests ---


async def test_get_next_concept_returns_lowest_mastery(
    service, mock_cache, user_id, org_id, concept_ids,
):
    path_data = {
        "user_id": str(user_id),
        "organization_id": str(org_id),
        "current_index": 0,
        "created_at": "2026-01-01T00:00:00",
        "concepts_ordered": [
            {
                "concept_id": str(concept_ids[0]),
                "name": "Python Basics",
                "priority": 1,
                "estimated_sessions": 1,
                "prerequisites": [],
                "mastery": 0.8,
            },
            {
                "concept_id": str(concept_ids[1]),
                "name": "OOP",
                "priority": 1,
                "estimated_sessions": 3,
                "prerequisites": [],
                "mastery": 0.3,
            },
        ],
    }
    mock_cache.get_path.return_value = json.dumps(path_data)

    result = await service.get_next_concept(user_id, org_id)

    assert result is not None
    assert result.name == "OOP"
    assert result.mastery == 0.3


async def test_get_next_concept_returns_none_when_all_mastered(
    service, mock_cache, user_id, org_id, concept_ids,
):
    path_data = {
        "user_id": str(user_id),
        "organization_id": str(org_id),
        "current_index": 0,
        "created_at": "2026-01-01T00:00:00",
        "concepts_ordered": [
            {
                "concept_id": str(concept_ids[0]),
                "name": "Python Basics",
                "priority": 1,
                "estimated_sessions": 1,
                "prerequisites": [],
                "mastery": 0.9,
            },
        ],
    }
    mock_cache.get_path.return_value = json.dumps(path_data)

    result = await service.get_next_concept(user_id, org_id)

    assert result is None


# --- adapt_path tests ---


async def test_adapt_path_inserts_remedial_on_low_score(
    service, mock_cache, user_id, org_id, concept_ids,
):
    path_data = {
        "user_id": str(user_id),
        "organization_id": str(org_id),
        "current_index": 1,
        "created_at": "2026-01-01T00:00:00",
        "concepts_ordered": [
            {
                "concept_id": str(concept_ids[0]),
                "name": "Python Basics",
                "priority": 1,
                "estimated_sessions": 1,
                "prerequisites": [],
                "mastery": 0.8,
            },
            {
                "concept_id": str(concept_ids[1]),
                "name": "OOP",
                "priority": 1,
                "estimated_sessions": 3,
                "prerequisites": [str(concept_ids[0])],
                "mastery": 0.3,
            },
        ],
    }
    mock_cache.get_path.return_value = json.dumps(path_data)

    session_result = {
        "concept_id": str(concept_ids[1]),
        "score": 0.4,
    }

    result = await service.adapt_path(user_id, org_id, session_result)

    assert isinstance(result, LearningPath)
    # Python Basics (prerequisite) should now appear before OOP with boosted priority
    names = [c.name for c in result.concepts_ordered]
    oop_idx = names.index("OOP")
    basics_idx = names.index("Python Basics")
    assert basics_idx < oop_idx


async def test_adapt_path_skips_on_high_score(
    service, mock_cache, user_id, org_id, concept_ids,
):
    path_data = {
        "user_id": str(user_id),
        "organization_id": str(org_id),
        "current_index": 0,
        "created_at": "2026-01-01T00:00:00",
        "concepts_ordered": [
            {
                "concept_id": str(concept_ids[0]),
                "name": "Python Basics",
                "priority": 1,
                "estimated_sessions": 3,
                "prerequisites": [],
                "mastery": 0.5,
            },
            {
                "concept_id": str(concept_ids[1]),
                "name": "OOP",
                "priority": 1,
                "estimated_sessions": 3,
                "prerequisites": [],
                "mastery": 0.3,
            },
        ],
    }
    mock_cache.get_path.return_value = json.dumps(path_data)

    session_result = {
        "concept_id": str(concept_ids[0]),
        "score": 0.95,
    }

    result = await service.adapt_path(user_id, org_id, session_result)

    basics = next(c for c in result.concepts_ordered if c.name == "Python Basics")
    assert basics.estimated_sessions == 0


async def test_adapt_path_saves_updated_path(
    service, mock_cache, user_id, org_id, concept_ids,
):
    path_data = {
        "user_id": str(user_id),
        "organization_id": str(org_id),
        "current_index": 0,
        "created_at": "2026-01-01T00:00:00",
        "concepts_ordered": [
            {
                "concept_id": str(concept_ids[0]),
                "name": "Python Basics",
                "priority": 1,
                "estimated_sessions": 3,
                "prerequisites": [],
                "mastery": 0.5,
            },
        ],
    }
    mock_cache.get_path.return_value = json.dumps(path_data)

    session_result = {
        "concept_id": str(concept_ids[0]),
        "score": 0.95,
    }

    await service.adapt_path(user_id, org_id, session_result)

    mock_cache.set_path.assert_called_once()
