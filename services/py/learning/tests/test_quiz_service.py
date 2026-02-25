from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import asyncpg
import pytest

from common.errors import ConflictError, ForbiddenError, NotFoundError
from app.domain.quiz import QuestionResult


class TestCreateQuiz:
    async def test_create_quiz_as_teacher(
        self, quiz_service, mock_repo, sample_quiz, sample_questions, teacher_id, lesson_id, course_id,
    ):
        mock_repo.create_quiz.return_value = sample_quiz
        mock_repo.create_questions.return_value = sample_questions

        questions_input = [
            {"text": f"Question {i}?", "options": ["A", "B", "C", "D"], "correct_index": i % 4, "explanation": f"Because {i}"}
            for i in range(5)
        ]

        quiz, questions = await quiz_service.create_quiz(
            teacher_id=teacher_id, role="teacher", is_verified=True,
            lesson_id=lesson_id, course_id=course_id, questions=questions_input,
        )

        assert quiz == sample_quiz
        assert questions == sample_questions
        mock_repo.create_quiz.assert_awaited_once_with(lesson_id, course_id, teacher_id)
        mock_repo.create_questions.assert_awaited_once()

    async def test_create_quiz_student_forbidden(
        self, quiz_service, lesson_id, course_id,
    ):
        with pytest.raises(ForbiddenError):
            await quiz_service.create_quiz(
                teacher_id=uuid4(), role="student", is_verified=False,
                lesson_id=lesson_id, course_id=course_id, questions=[],
            )

    async def test_create_quiz_unverified_teacher_forbidden(
        self, quiz_service, lesson_id, course_id,
    ):
        with pytest.raises(ForbiddenError):
            await quiz_service.create_quiz(
                teacher_id=uuid4(), role="teacher", is_verified=False,
                lesson_id=lesson_id, course_id=course_id, questions=[],
            )

    async def test_create_quiz_duplicate_lesson_conflict(
        self, quiz_service, mock_repo, teacher_id, lesson_id, course_id,
    ):
        mock_repo.create_quiz.side_effect = asyncpg.UniqueViolationError()

        with pytest.raises(ConflictError):
            await quiz_service.create_quiz(
                teacher_id=teacher_id, role="teacher", is_verified=True,
                lesson_id=lesson_id, course_id=course_id,
                questions=[{"text": "Q?", "options": ["A", "B"], "correct_index": 0}],
            )


class TestGetQuiz:
    async def test_get_quiz_by_lesson(
        self, quiz_service, mock_repo, sample_quiz, sample_questions, lesson_id,
    ):
        mock_repo.get_quiz_by_lesson.return_value = sample_quiz
        mock_repo.get_questions.return_value = sample_questions

        quiz, questions = await quiz_service.get_quiz_by_lesson(lesson_id)

        assert quiz == sample_quiz
        assert questions == sample_questions
        mock_repo.get_quiz_by_lesson.assert_awaited_once_with(lesson_id)
        mock_repo.get_questions.assert_awaited_once_with(sample_quiz.id)

    async def test_get_quiz_not_found(self, quiz_service, mock_repo, lesson_id):
        mock_repo.get_quiz_by_lesson.return_value = None

        with pytest.raises(NotFoundError):
            await quiz_service.get_quiz_by_lesson(lesson_id)


class TestSubmitQuiz:
    async def test_submit_scores_correctly(
        self, quiz_service, mock_repo, sample_quiz, sample_questions, sample_attempt, student_id, quiz_id,
    ):
        mock_repo.get_quiz_by_id.return_value = sample_quiz
        mock_repo.get_questions.return_value = sample_questions
        # All correct answers: correct_index for question i is i % 4
        correct_answers = [q.correct_index for q in sample_questions]
        perfect_attempt = sample_attempt  # we override score via mock
        mock_repo.create_attempt.return_value = perfect_attempt

        attempt, results = await quiz_service.submit_quiz(
            quiz_id=quiz_id, student_id=student_id, role="student", answers=correct_answers,
        )

        assert attempt == perfect_attempt
        assert all(r.is_correct for r in results)
        # Verify score passed to repo is 1.0
        call_kwargs = mock_repo.create_attempt.call_args
        assert call_kwargs.kwargs["score"] == 1.0

    async def test_submit_partial_correct(
        self, quiz_service, mock_repo, sample_quiz, sample_questions, sample_attempt, student_id, quiz_id,
    ):
        mock_repo.get_quiz_by_id.return_value = sample_quiz
        mock_repo.get_questions.return_value = sample_questions
        # All wrong answers (offset by 1 from correct)
        wrong_answers = [(q.correct_index + 1) % 4 for q in sample_questions]
        # Make first answer correct
        wrong_answers[0] = sample_questions[0].correct_index
        mock_repo.create_attempt.return_value = sample_attempt

        attempt, results = await quiz_service.submit_quiz(
            quiz_id=quiz_id, student_id=student_id, role="student", answers=wrong_answers,
        )

        assert results[0].is_correct is True
        assert all(r.is_correct is False for r in results[1:])
        call_kwargs = mock_repo.create_attempt.call_args
        assert call_kwargs.kwargs["score"] == pytest.approx(1 / len(sample_questions))

    async def test_submit_quiz_not_found(self, quiz_service, mock_repo, student_id, quiz_id):
        mock_repo.get_quiz_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await quiz_service.submit_quiz(
                quiz_id=quiz_id, student_id=student_id, role="student", answers=[0],
            )

    async def test_submit_wrong_answer_count(
        self, quiz_service, mock_repo, sample_quiz, sample_questions, student_id, quiz_id,
    ):
        mock_repo.get_quiz_by_id.return_value = sample_quiz
        mock_repo.get_questions.return_value = sample_questions

        with pytest.raises(ValueError, match="Expected 5 answers, got 2"):
            await quiz_service.submit_quiz(
                quiz_id=quiz_id, student_id=student_id, role="student", answers=[0, 1],
            )

    async def test_submit_teacher_forbidden(self, quiz_service, quiz_id):
        with pytest.raises(ForbiddenError):
            await quiz_service.submit_quiz(
                quiz_id=quiz_id, student_id=uuid4(), role="teacher", answers=[0],
            )


class TestListAttempts:
    async def test_list_my_attempts(
        self, quiz_service, mock_repo, sample_attempt, student_id, quiz_id,
    ):
        mock_repo.list_attempts.return_value = ([sample_attempt], 1)

        attempts, total = await quiz_service.list_my_attempts(quiz_id, student_id)

        assert attempts == [sample_attempt]
        assert total == 1
        mock_repo.list_attempts.assert_awaited_once_with(quiz_id, student_id, 20, 0)
