from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.flashcard import Flashcard
from app.domain.mission import Mission
from app.services.flashcard_service import FlashcardService
from app.services.review_generator import ReviewGenerator


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def mock_flashcard_service():
    return AsyncMock(spec=FlashcardService)


@pytest.fixture
def review_generator(mock_flashcard_service):
    return ReviewGenerator(flashcard_service=mock_flashcard_service)


def _make_mission(
    user_id,
    org_id,
    *,
    check_questions: list[dict] | None = None,
    code_case: dict | None = None,
) -> Mission:
    blueprint = {}
    if check_questions is not None:
        blueprint["check_questions"] = check_questions
    if code_case is not None:
        blueprint["code_case"] = code_case
    return Mission(
        id=uuid4(),
        user_id=user_id,
        organization_id=org_id,
        concept_id=uuid4(),
        mission_type="daily",
        status="completed",
        blueprint=blueprint,
        score=0.8,
        mastery_delta=0.1,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


def _fake_flashcard(card_id, student_id, course_id):
    return Flashcard(
        id=card_id,
        student_id=student_id,
        course_id=course_id,
        concept="Q",
        answer="A",
        source_type="mission",
        source_id=None,
        stability=0.0,
        difficulty=0.0,
        due=datetime.now(timezone.utc),
        last_review=None,
        reps=0,
        lapses=0,
        state=0,
        created_at=datetime.now(timezone.utc),
    )


class TestReviewGenerator:
    async def test_generates_flashcards_from_check_questions(
        self, review_generator, mock_flashcard_service, user_id, org_id,
    ):
        check_questions = [
            {"question": "What is a variable?", "explanation": "A named storage location"},
            {"question": "What is a loop?", "explanation": "A control structure for repetition"},
            {"question": "What is a function?", "explanation": "A reusable block of code"},
        ]
        mission = _make_mission(user_id, org_id, check_questions=check_questions)

        card_id = uuid4()
        mock_flashcard_service.create_card.return_value = _fake_flashcard(card_id, user_id, org_id)

        result = await review_generator.generate_from_mission(user_id, mission)

        assert len(result) == 3
        assert mock_flashcard_service.create_card.await_count == 3

        calls = mock_flashcard_service.create_card.call_args_list
        for i, call in enumerate(calls):
            assert call.kwargs["student_id"] == user_id
            assert call.kwargs["role"] == "student"
            assert call.kwargs["course_id"] == mission.organization_id
            assert call.kwargs["concept"] == check_questions[i]["question"]
            assert call.kwargs["answer"] == check_questions[i]["explanation"]
            assert call.kwargs["source_type"] == "mission"
            assert call.kwargs["source_id"] == mission.id

    async def test_generates_flashcard_from_code_case(
        self, review_generator, mock_flashcard_service, user_id, org_id,
    ):
        code_case = {
            "question": "Write a fibonacci function",
            "expected_answer": "def fib(n): return n if n <= 1 else fib(n-1) + fib(n-2)",
        }
        mission = _make_mission(user_id, org_id, code_case=code_case)

        card_id = uuid4()
        mock_flashcard_service.create_card.return_value = _fake_flashcard(card_id, user_id, org_id)

        result = await review_generator.generate_from_mission(user_id, mission)

        assert len(result) == 1
        mock_flashcard_service.create_card.assert_awaited_once_with(
            student_id=user_id,
            role="student",
            course_id=mission.organization_id,
            concept=code_case["question"],
            answer=code_case["expected_answer"],
            source_type="mission",
            source_id=mission.id,
        )

    async def test_3_check_questions_plus_1_code_case_equals_4_flashcards(
        self, review_generator, mock_flashcard_service, user_id, org_id,
    ):
        check_questions = [
            {"question": f"Q{i}?", "explanation": f"A{i}"} for i in range(3)
        ]
        code_case = {"question": "Code Q", "expected_answer": "Code A"}
        mission = _make_mission(
            user_id, org_id, check_questions=check_questions, code_case=code_case,
        )

        card_id = uuid4()
        mock_flashcard_service.create_card.return_value = _fake_flashcard(card_id, user_id, org_id)

        result = await review_generator.generate_from_mission(user_id, mission)

        assert len(result) == 4
        assert mock_flashcard_service.create_card.await_count == 4

    async def test_empty_blueprint_returns_no_flashcards(
        self, review_generator, mock_flashcard_service, user_id, org_id,
    ):
        mission = _make_mission(user_id, org_id)

        result = await review_generator.generate_from_mission(user_id, mission)

        assert result == []
        mock_flashcard_service.create_card.assert_not_awaited()

    async def test_flashcard_creation_failure_is_logged_not_raised(
        self, review_generator, mock_flashcard_service, user_id, org_id,
    ):
        check_questions = [{"question": "Q?", "explanation": "A"}]
        mission = _make_mission(user_id, org_id, check_questions=check_questions)

        mock_flashcard_service.create_card.side_effect = Exception("DB error")

        result = await review_generator.generate_from_mission(user_id, mission)

        assert result == []
