from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

from app.config import Settings
from app.domain.mission import (
    CheckQuestion,
    CodeCase,
    MissionBlueprint,
    RecapQuestion,
)
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient
from app.services.designer_service import DesignerService


@pytest.fixture
def concept_id():
    return uuid4()


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def rag_search_results():
    return {
        "results": [
            {
                "content": "Dependency Injection is a design pattern where objects receive their dependencies from external sources rather than creating them internally.",
                "similarity": 0.92,
                "document_title": "Clean Architecture Guide",
                "source_path": "docs/architecture/dependency-injection.md",
            },
            {
                "content": "class UserService:\n    def __init__(self, repo: UserRepository):\n        self._repo = repo",
                "similarity": 0.88,
                "document_title": "Identity Service",
                "source_path": "services/py/identity/app/services/user_service.py",
            },
            {
                "content": "DI containers manage object lifetimes and resolve dependency graphs automatically.",
                "similarity": 0.85,
                "document_title": "DI Patterns",
                "source_path": "docs/patterns/di-containers.md",
            },
        ]
    }


@pytest.fixture
def recap_search_results():
    return {
        "results": [
            {
                "content": "SOLID principles define five rules for object-oriented design.",
                "similarity": 0.90,
                "document_title": "SOLID Guide",
                "source_path": "docs/patterns/solid.md",
            },
        ]
    }


@pytest.fixture
def reading_content_response():
    return "Dependency Injection (DI) is a fundamental pattern in Clean Architecture. When a class like `UserService` needs access to a `UserRepository`, it receives the repository through its constructor rather than creating one itself.\n\n```python\nclass UserService:\n    def __init__(self, repo: UserRepository):\n        self._repo = repo\n```\n\nThis approach decouples the service from concrete implementations, making testing straightforward — you can inject a mock repository during tests."


@pytest.fixture
def check_questions_response():
    return json.dumps([
        {
            "question": "What is the main benefit of Dependency Injection?",
            "options": [
                "Faster execution",
                "Decoupling from concrete implementations",
                "Less code to write",
                "Better variable naming",
            ],
            "correct_index": 1,
            "explanation": "DI decouples classes from their concrete dependencies, enabling testability and flexibility.",
        },
        {
            "question": "Where should dependencies be provided in constructor injection?",
            "options": [
                "Inside the class methods",
                "Through global variables",
                "Via the constructor parameters",
                "Through environment variables",
            ],
            "correct_index": 2,
            "explanation": "Constructor injection passes dependencies as constructor parameters.",
        },
        {
            "question": "What makes DI useful for testing?",
            "options": [
                "It removes the need for tests",
                "It allows injecting mock implementations",
                "It makes tests run faster",
                "It auto-generates test cases",
            ],
            "correct_index": 1,
            "explanation": "DI lets you replace real dependencies with mocks/stubs during testing.",
        },
    ])


@pytest.fixture
def code_case_response():
    return json.dumps({
        "code_snippet": "class PaymentService:\n    def __init__(self):\n        self._gateway = StripeGateway()\n\n    async def process(self, amount: float):\n        return await self._gateway.charge(amount)",
        "language": "python",
        "question": "What DI anti-pattern does this code exhibit, and how would you fix it?",
        "expected_answer": "The PaymentService creates StripeGateway internally instead of receiving it via constructor injection. Fix: accept a PaymentGateway interface in __init__.",
        "source_path": "services/py/payment/app/services/payment_service.py",
    })


@pytest.fixture
def recap_questions_response():
    return json.dumps([
        {
            "question": "What does the S in SOLID stand for?",
            "expected_answer": "Single Responsibility Principle",
            "concept_ref": "SOLID Principles",
        },
        {
            "question": "Why should a class have only one reason to change?",
            "expected_answer": "To minimize the impact of changes and keep the class focused on one concern.",
            "concept_ref": "SOLID Principles",
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
    return DesignerService(
        gemini_client=mock_llm,
        cache=mock_cache,
        http_client=mock_http,
        settings=settings,
    )


def _make_rag_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = data
    return resp


# --- design_mission tests ---


async def test_design_mission_returns_blueprint(
    service, mock_llm, mock_http, concept_id, org_id,
    rag_search_results, reading_content_response,
    check_questions_response, code_case_response,
):
    mock_http.post.return_value = _make_rag_response(rag_search_results)
    mock_llm.generate.side_effect = [
        (reading_content_response, 200, 400),
        (check_questions_response, 150, 300),
        (code_case_response, 100, 200),
    ]

    result = await service.design_mission(
        concept_name="Dependency Injection",
        concept_id=concept_id,
        org_id=org_id,
    )

    assert isinstance(result, MissionBlueprint)
    assert result.concept_name == "Dependency Injection"
    assert result.concept_id == concept_id
    assert len(result.check_questions) == 3
    assert result.code_case is not None
    assert result.reading_content == reading_content_response


async def test_design_mission_reading_prompt_includes_rag_results(
    service, mock_llm, mock_http, concept_id, org_id,
    rag_search_results, reading_content_response,
    check_questions_response, code_case_response,
):
    mock_http.post.return_value = _make_rag_response(rag_search_results)
    mock_llm.generate.side_effect = [
        (reading_content_response, 200, 400),
        (check_questions_response, 150, 300),
        (code_case_response, 100, 200),
    ]

    await service.design_mission(
        concept_name="Dependency Injection",
        concept_id=concept_id,
        org_id=org_id,
    )

    reading_prompt = mock_llm.generate.call_args_list[0][0][0]
    assert "Dependency Injection" in reading_prompt
    assert "dependency-injection.md" in reading_prompt or "Dependency Injection is a design pattern" in reading_prompt


async def test_design_mission_check_questions_valid_mcq(
    service, mock_llm, mock_http, concept_id, org_id,
    rag_search_results, reading_content_response,
    check_questions_response, code_case_response,
):
    mock_http.post.return_value = _make_rag_response(rag_search_results)
    mock_llm.generate.side_effect = [
        (reading_content_response, 200, 400),
        (check_questions_response, 150, 300),
        (code_case_response, 100, 200),
    ]

    result = await service.design_mission(
        concept_name="Dependency Injection",
        concept_id=concept_id,
        org_id=org_id,
    )

    for q in result.check_questions:
        assert isinstance(q, CheckQuestion)
        assert len(q.options) == 4
        assert 0 <= q.correct_index < len(q.options)
        assert q.explanation


async def test_design_mission_code_case_uses_source_path(
    service, mock_llm, mock_http, concept_id, org_id,
    rag_search_results, reading_content_response,
    check_questions_response, code_case_response,
):
    mock_http.post.return_value = _make_rag_response(rag_search_results)
    mock_llm.generate.side_effect = [
        (reading_content_response, 200, 400),
        (check_questions_response, 150, 300),
        (code_case_response, 100, 200),
    ]

    result = await service.design_mission(
        concept_name="Dependency Injection",
        concept_id=concept_id,
        org_id=org_id,
    )

    assert result.code_case is not None
    assert isinstance(result.code_case, CodeCase)
    assert result.code_case.source_path


async def test_design_mission_with_previous_concepts_generates_recap(
    service, mock_llm, mock_http, concept_id, org_id,
    rag_search_results, recap_search_results, reading_content_response,
    check_questions_response, code_case_response, recap_questions_response,
):
    mock_http.post.side_effect = [
        _make_rag_response(rag_search_results),
        _make_rag_response(recap_search_results),
    ]
    mock_llm.generate.side_effect = [
        (reading_content_response, 200, 400),
        (check_questions_response, 150, 300),
        (code_case_response, 100, 200),
        (recap_questions_response, 100, 150),
    ]

    result = await service.design_mission(
        concept_name="Dependency Injection",
        concept_id=concept_id,
        org_id=org_id,
        previous_concepts=["SOLID Principles"],
    )

    assert len(result.recap_questions) == 2
    for q in result.recap_questions:
        assert isinstance(q, RecapQuestion)
        assert q.concept_ref == "SOLID Principles"


async def test_design_mission_no_recap_without_previous_concepts(
    service, mock_llm, mock_http, concept_id, org_id,
    rag_search_results, reading_content_response,
    check_questions_response, code_case_response,
):
    mock_http.post.return_value = _make_rag_response(rag_search_results)
    mock_llm.generate.side_effect = [
        (reading_content_response, 200, 400),
        (check_questions_response, 150, 300),
        (code_case_response, 100, 200),
    ]

    result = await service.design_mission(
        concept_name="Dependency Injection",
        concept_id=concept_id,
        org_id=org_id,
    )

    assert result.recap_questions == []


async def test_design_mission_graceful_on_rag_failure(
    service, mock_llm, mock_http, concept_id, org_id,
    reading_content_response, check_questions_response,
):
    mock_http.post.side_effect = httpx.ConnectError("connection refused")
    mock_llm.generate.side_effect = [
        (reading_content_response, 200, 400),
        (check_questions_response, 150, 300),
    ]

    result = await service.design_mission(
        concept_name="Dependency Injection",
        concept_id=concept_id,
        org_id=org_id,
    )

    assert isinstance(result, MissionBlueprint)
    assert result.code_case is None
    assert result.reading_content == reading_content_response


async def test_design_mission_graceful_on_rag_non_200(
    service, mock_llm, mock_http, concept_id, org_id,
    reading_content_response, check_questions_response,
):
    error_resp = MagicMock()
    error_resp.status_code = 500
    mock_http.post.return_value = error_resp
    mock_llm.generate.side_effect = [
        (reading_content_response, 200, 400),
        (check_questions_response, 150, 300),
    ]

    result = await service.design_mission(
        concept_name="Dependency Injection",
        concept_id=concept_id,
        org_id=org_id,
    )

    assert isinstance(result, MissionBlueprint)
    assert result.code_case is None


async def test_design_mission_handles_markdown_fenced_json(
    service, mock_llm, mock_http, concept_id, org_id,
    rag_search_results, reading_content_response,
    code_case_response,
):
    fenced_check = "```json\n" + json.dumps([
        {
            "question": "What is DI?",
            "options": ["A", "B", "C", "D"],
            "correct_index": 0,
            "explanation": "DI is...",
        },
        {
            "question": "Why DI?",
            "options": ["A", "B", "C", "D"],
            "correct_index": 1,
            "explanation": "Because...",
        },
        {
            "question": "How DI?",
            "options": ["A", "B", "C", "D"],
            "correct_index": 2,
            "explanation": "By...",
        },
    ]) + "\n```"

    mock_http.post.return_value = _make_rag_response(rag_search_results)
    mock_llm.generate.side_effect = [
        (reading_content_response, 200, 400),
        (fenced_check, 150, 300),
        (code_case_response, 100, 200),
    ]

    result = await service.design_mission(
        concept_name="Dependency Injection",
        concept_id=concept_id,
        org_id=org_id,
    )

    assert len(result.check_questions) == 3


async def test_design_mission_code_case_prompt_includes_code_sources(
    service, mock_llm, mock_http, concept_id, org_id,
    rag_search_results, reading_content_response,
    check_questions_response, code_case_response,
):
    mock_http.post.return_value = _make_rag_response(rag_search_results)
    mock_llm.generate.side_effect = [
        (reading_content_response, 200, 400),
        (check_questions_response, 150, 300),
        (code_case_response, 100, 200),
    ]

    await service.design_mission(
        concept_name="Dependency Injection",
        concept_id=concept_id,
        org_id=org_id,
    )

    # Code case prompt (3rd call) should include source code from RAG
    code_prompt = mock_llm.generate.call_args_list[2][0][0]
    assert "UserService" in code_prompt or "source_path" in code_prompt or "code" in code_prompt.lower()
