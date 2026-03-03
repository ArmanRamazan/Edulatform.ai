from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4, UUID

from app.domain.concept import Concept, ConceptMastery
from app.domain.pretest import Pretest, PretestAnswer
from app.repositories.pretest_repo import PretestRepository
from app.repositories.concept_repo import ConceptRepository
from app.services.pretest_service import (
    PretestService,
    generate_question,
    pick_next_concept,
)
from common.errors import ConflictError, NotFoundError


# ── Fixtures ──


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def course_id() -> UUID:
    return uuid4()


@pytest.fixture
def pretest_id() -> UUID:
    return uuid4()


def _make_concept(
    course_id: UUID, order: int, name: str = "", concept_id: UUID | None = None
) -> Concept:
    return Concept(
        id=concept_id or uuid4(),
        course_id=course_id,
        lesson_id=None,
        name=name or f"Concept_{order}",
        description=f"Description of concept at order {order}",
        parent_id=None,
        order=order,
        created_at=datetime.now(timezone.utc),
    )


def _make_pretest(
    pretest_id: UUID, user_id: UUID, course_id: UUID, status: str = "in_progress"
) -> Pretest:
    return Pretest(
        id=pretest_id,
        user_id=user_id,
        course_id=course_id,
        started_at=datetime.now(timezone.utc),
        completed_at=None if status == "in_progress" else datetime.now(timezone.utc),
        status=status,
    )


def _make_answer(
    pretest_id: UUID,
    concept_id: UUID,
    is_correct: bool | None = None,
    user_answer: str | None = None,
    answer_id: UUID | None = None,
) -> PretestAnswer:
    return PretestAnswer(
        id=answer_id or uuid4(),
        pretest_id=pretest_id,
        concept_id=concept_id,
        question="True or False: some description",
        user_answer=user_answer,
        correct_answer="True",
        is_correct=is_correct,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_pretest_repo() -> AsyncMock:
    return AsyncMock(spec=PretestRepository)


@pytest.fixture
def mock_concept_repo() -> AsyncMock:
    return AsyncMock(spec=ConceptRepository)


@pytest.fixture
def pretest_service(mock_pretest_repo: AsyncMock, mock_concept_repo: AsyncMock) -> PretestService:
    return PretestService(
        pretest_repo=mock_pretest_repo,
        concept_repo=mock_concept_repo,
    )


# ── Pure function tests ──


class TestGenerateQuestion:
    def test_returns_true_false_question(self, course_id: UUID) -> None:
        concept = _make_concept(course_id, order=0, name="Variables")
        question, answer = generate_question(concept)
        assert "True or False" in question
        assert concept.description in question
        assert answer == "True"


class TestPickNextConcept:
    def test_first_question_picks_middle(self, course_id: UUID) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(5)]
        result = pick_next_concept(concepts, set(), last_correct=None)
        assert result is not None
        assert result.order == 2  # middle of [0,1,2,3,4]

    def test_correct_answer_picks_harder(self, course_id: UUID) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(5)]
        tested = {concepts[2].id}  # already tested middle
        result = pick_next_concept(concepts, tested, last_correct=True)
        assert result is not None
        assert result.order == 4  # highest order among untested

    def test_wrong_answer_picks_easier(self, course_id: UUID) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(5)]
        tested = {concepts[2].id}  # already tested middle
        result = pick_next_concept(concepts, tested, last_correct=False)
        assert result is not None
        assert result.order == 0  # lowest order among untested

    def test_all_tested_returns_none(self, course_id: UUID) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(3)]
        tested = {c.id for c in concepts}
        result = pick_next_concept(concepts, tested, last_correct=True)
        assert result is None

    def test_single_untested_concept(self, course_id: UUID) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(3)]
        tested = {concepts[0].id, concepts[2].id}
        result = pick_next_concept(concepts, tested, last_correct=True)
        assert result is not None
        assert result.id == concepts[1].id


# ── Service tests ──


class TestStartPretest:
    async def test_start_new_pretest(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        mock_concept_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(5)]
        pretest = _make_pretest(pretest_id, user_id, course_id)
        answer = _make_answer(pretest_id, concepts[2].id)

        mock_pretest_repo.get_by_user_and_course.return_value = None
        mock_concept_repo.get_by_course.return_value = concepts
        mock_pretest_repo.create_pretest.return_value = pretest
        mock_pretest_repo.add_answer.return_value = answer

        result = await pretest_service.start_pretest(user_id, course_id)

        assert result["pretest_id"] == pretest_id
        assert result["total_concepts"] == 5
        assert "question" in result
        assert "concept_id" in result
        assert "answer_id" in result
        mock_pretest_repo.create_pretest.assert_awaited_once_with(user_id, course_id)

    async def test_return_existing_in_progress(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        mock_concept_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(5)]
        pretest = _make_pretest(pretest_id, user_id, course_id, status="in_progress")
        unanswered = _make_answer(pretest_id, concepts[0].id, is_correct=None)

        mock_pretest_repo.get_by_user_and_course.return_value = pretest
        mock_pretest_repo.get_answers.return_value = [unanswered]
        mock_concept_repo.get_by_course.return_value = concepts

        result = await pretest_service.start_pretest(user_id, course_id)

        assert result["pretest_id"] == pretest_id
        mock_pretest_repo.create_pretest.assert_not_awaited()

    async def test_error_if_already_completed(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        pretest = _make_pretest(pretest_id, user_id, course_id, status="completed")
        mock_pretest_repo.get_by_user_and_course.return_value = pretest

        with pytest.raises(ConflictError, match="already completed"):
            await pretest_service.start_pretest(user_id, course_id)

    async def test_error_if_no_concepts(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        mock_concept_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
    ) -> None:
        mock_pretest_repo.get_by_user_and_course.return_value = None
        mock_concept_repo.get_by_course.return_value = []

        with pytest.raises(NotFoundError, match="No concepts"):
            await pretest_service.start_pretest(user_id, course_id)


class TestAnswerAndNext:
    async def test_correct_answer_leads_to_harder_concept(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        mock_concept_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(5)]
        pretest = _make_pretest(pretest_id, user_id, course_id)
        answer_id = uuid4()
        current_answer = _make_answer(
            pretest_id, concepts[2].id, answer_id=answer_id
        )
        updated_answer = PretestAnswer(
            id=answer_id,
            pretest_id=pretest_id,
            concept_id=concepts[2].id,
            question=current_answer.question,
            user_answer="True",
            correct_answer="True",
            is_correct=True,
            created_at=current_answer.created_at,
        )
        next_answer = _make_answer(pretest_id, concepts[4].id)

        mock_pretest_repo.get_by_id.return_value = pretest
        mock_pretest_repo.get_answers.return_value = [current_answer]
        mock_pretest_repo.update_answer.return_value = updated_answer
        mock_concept_repo.get_by_course.return_value = concepts
        mock_pretest_repo.add_answer.return_value = next_answer

        result = await pretest_service.answer_and_next(
            pretest_id, answer_id, "True", user_id
        )

        assert result["completed"] is False
        assert result["concept_id"] == concepts[4].id
        assert result["next_question"] is not None

    async def test_wrong_answer_leads_to_easier_concept(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        mock_concept_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(5)]
        pretest = _make_pretest(pretest_id, user_id, course_id)
        answer_id = uuid4()
        current_answer = _make_answer(
            pretest_id, concepts[2].id, answer_id=answer_id
        )
        updated_answer = PretestAnswer(
            id=answer_id,
            pretest_id=pretest_id,
            concept_id=concepts[2].id,
            question=current_answer.question,
            user_answer="False",
            correct_answer="True",
            is_correct=False,
            created_at=current_answer.created_at,
        )
        next_answer = _make_answer(pretest_id, concepts[0].id)

        mock_pretest_repo.get_by_id.return_value = pretest
        mock_pretest_repo.get_answers.return_value = [current_answer]
        mock_pretest_repo.update_answer.return_value = updated_answer
        mock_concept_repo.get_by_course.return_value = concepts
        mock_pretest_repo.add_answer.return_value = next_answer

        result = await pretest_service.answer_and_next(
            pretest_id, answer_id, "False", user_id
        )

        assert result["completed"] is False
        assert result["concept_id"] == concepts[0].id

    async def test_completes_after_all_concepts_tested(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        mock_concept_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(3)]
        pretest = _make_pretest(pretest_id, user_id, course_id)
        answer_id = uuid4()

        # 2 already answered, answering the 3rd (last)
        answered_1 = _make_answer(pretest_id, concepts[0].id, is_correct=True, user_answer="True")
        answered_2 = _make_answer(pretest_id, concepts[1].id, is_correct=False, user_answer="False")
        current_answer = _make_answer(pretest_id, concepts[2].id, answer_id=answer_id)

        updated_answer = PretestAnswer(
            id=answer_id,
            pretest_id=pretest_id,
            concept_id=concepts[2].id,
            question=current_answer.question,
            user_answer="True",
            correct_answer="True",
            is_correct=True,
            created_at=current_answer.created_at,
        )
        completed_pretest = _make_pretest(pretest_id, user_id, course_id, status="completed")

        mock_pretest_repo.get_by_id.return_value = pretest
        mock_pretest_repo.get_answers.return_value = [answered_1, answered_2, current_answer]
        mock_pretest_repo.update_answer.return_value = updated_answer
        mock_concept_repo.get_by_course.return_value = concepts
        mock_pretest_repo.complete_pretest.return_value = completed_pretest
        mock_concept_repo.upsert_mastery.return_value = None

        result = await pretest_service.answer_and_next(
            pretest_id, answer_id, "True", user_id
        )

        assert result["completed"] is True
        assert "results" in result
        mock_pretest_repo.complete_pretest.assert_awaited_once_with(pretest_id)
        # 3 concepts answered: 2 correct (0.7) + 1 wrong (0.1)
        assert mock_concept_repo.upsert_mastery.await_count == 3

    async def test_completes_after_min_5_questions(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        mock_concept_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        # 10 concepts but should complete after 5 answered
        concepts = [_make_concept(course_id, order=i) for i in range(10)]
        pretest = _make_pretest(pretest_id, user_id, course_id)
        answer_id = uuid4()

        # 4 already answered, this is the 5th
        answered = [
            _make_answer(pretest_id, concepts[i].id, is_correct=True, user_answer="True")
            for i in range(4)
        ]
        current_answer = _make_answer(pretest_id, concepts[4].id, answer_id=answer_id)
        answered.append(current_answer)

        updated_answer = PretestAnswer(
            id=answer_id,
            pretest_id=pretest_id,
            concept_id=concepts[4].id,
            question=current_answer.question,
            user_answer="True",
            correct_answer="True",
            is_correct=True,
            created_at=current_answer.created_at,
        )
        completed_pretest = _make_pretest(pretest_id, user_id, course_id, status="completed")

        mock_pretest_repo.get_by_id.return_value = pretest
        mock_pretest_repo.get_answers.return_value = answered
        mock_pretest_repo.update_answer.return_value = updated_answer
        mock_concept_repo.get_by_course.return_value = concepts
        mock_pretest_repo.complete_pretest.return_value = completed_pretest
        mock_concept_repo.upsert_mastery.return_value = None

        result = await pretest_service.answer_and_next(
            pretest_id, answer_id, "True", user_id
        )

        assert result["completed"] is True
        mock_pretest_repo.complete_pretest.assert_awaited_once()

    async def test_mastery_update_correct_answer(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        mock_concept_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(2)]
        pretest = _make_pretest(pretest_id, user_id, course_id)
        answer_id = uuid4()

        answered_1 = _make_answer(pretest_id, concepts[0].id, is_correct=True, user_answer="True")
        current_answer = _make_answer(pretest_id, concepts[1].id, answer_id=answer_id)

        updated_answer = PretestAnswer(
            id=answer_id,
            pretest_id=pretest_id,
            concept_id=concepts[1].id,
            question=current_answer.question,
            user_answer="True",
            correct_answer="True",
            is_correct=True,
            created_at=current_answer.created_at,
        )
        completed_pretest = _make_pretest(pretest_id, user_id, course_id, status="completed")

        mock_pretest_repo.get_by_id.return_value = pretest
        mock_pretest_repo.get_answers.return_value = [answered_1, current_answer]
        mock_pretest_repo.update_answer.return_value = updated_answer
        mock_concept_repo.get_by_course.return_value = concepts
        mock_pretest_repo.complete_pretest.return_value = completed_pretest
        mock_concept_repo.upsert_mastery.return_value = None

        await pretest_service.answer_and_next(pretest_id, answer_id, "True", user_id)

        # Both correct → mastery 0.7 each
        calls = mock_concept_repo.upsert_mastery.call_args_list
        mastery_values = {c.args[1]: c.args[2] for c in calls}
        assert mastery_values[concepts[0].id] == 0.7
        assert mastery_values[concepts[1].id] == 0.7

    async def test_mastery_update_wrong_answer(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        mock_concept_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        concepts = [_make_concept(course_id, order=i) for i in range(2)]
        pretest = _make_pretest(pretest_id, user_id, course_id)
        answer_id = uuid4()

        answered_1 = _make_answer(pretest_id, concepts[0].id, is_correct=False, user_answer="False")
        current_answer = _make_answer(pretest_id, concepts[1].id, answer_id=answer_id)

        updated_answer = PretestAnswer(
            id=answer_id,
            pretest_id=pretest_id,
            concept_id=concepts[1].id,
            question=current_answer.question,
            user_answer="False",
            correct_answer="True",
            is_correct=False,
            created_at=current_answer.created_at,
        )
        completed_pretest = _make_pretest(pretest_id, user_id, course_id, status="completed")

        mock_pretest_repo.get_by_id.return_value = pretest
        mock_pretest_repo.get_answers.return_value = [answered_1, current_answer]
        mock_pretest_repo.update_answer.return_value = updated_answer
        mock_concept_repo.get_by_course.return_value = concepts
        mock_pretest_repo.complete_pretest.return_value = completed_pretest
        mock_concept_repo.upsert_mastery.return_value = None

        await pretest_service.answer_and_next(pretest_id, answer_id, "False", user_id)

        calls = mock_concept_repo.upsert_mastery.call_args_list
        mastery_values = {c.args[1]: c.args[2] for c in calls}
        assert mastery_values[concepts[0].id] == 0.1
        assert mastery_values[concepts[1].id] == 0.1

    async def test_not_found_pretest(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        user_id: UUID,
    ) -> None:
        mock_pretest_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="Pretest not found"):
            await pretest_service.answer_and_next(uuid4(), uuid4(), "True", user_id)

    async def test_forbidden_other_user(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        from common.errors import ForbiddenError

        other_user = uuid4()
        pretest = _make_pretest(pretest_id, user_id, course_id)
        mock_pretest_repo.get_by_id.return_value = pretest

        with pytest.raises(ForbiddenError):
            await pretest_service.answer_and_next(pretest_id, uuid4(), "True", other_user)


class TestGetResults:
    async def test_returns_results(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        mock_concept_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
        pretest_id: UUID,
    ) -> None:
        concepts = [_make_concept(course_id, order=i, name=f"C{i}") for i in range(3)]
        pretest = _make_pretest(pretest_id, user_id, course_id, status="completed")

        answers = [
            _make_answer(pretest_id, concepts[0].id, is_correct=True, user_answer="True"),
            _make_answer(pretest_id, concepts[2].id, is_correct=False, user_answer="False"),
        ]

        mock_pretest_repo.get_by_user_and_course.return_value = pretest
        mock_pretest_repo.get_answers.return_value = answers
        mock_concept_repo.get_by_course.return_value = concepts

        result = await pretest_service.get_results(user_id, course_id)

        assert result["course_id"] == course_id
        assert len(result["concepts"]) == 3
        # concept 0 tested correct, concept 1 not tested, concept 2 tested wrong
        c0 = next(c for c in result["concepts"] if c["concept_id"] == concepts[0].id)
        c1 = next(c for c in result["concepts"] if c["concept_id"] == concepts[1].id)
        c2 = next(c for c in result["concepts"] if c["concept_id"] == concepts[2].id)
        assert c0["tested"] is True
        assert c0["mastery"] == 0.7
        assert c1["tested"] is False
        assert c1["mastery"] == 0.0
        assert c2["tested"] is True
        assert c2["mastery"] == 0.1
        assert 0.0 <= result["overall_readiness"] <= 1.0

    async def test_not_found_no_pretest(
        self,
        pretest_service: PretestService,
        mock_pretest_repo: AsyncMock,
        user_id: UUID,
        course_id: UUID,
    ) -> None:
        mock_pretest_repo.get_by_user_and_course.return_value = None

        with pytest.raises(NotFoundError, match="Pretest not found"):
            await pretest_service.get_results(user_id, course_id)
