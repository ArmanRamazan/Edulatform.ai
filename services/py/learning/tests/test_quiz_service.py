from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

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
        mock_repo.create_quiz.side_effect = ConflictError("Quiz already exists for this lesson")

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


class TestAutoGenerateFlashcards:
    async def test_wrong_answers_create_flashcards(
        self, quiz_service_with_flashcards, mock_repo, mock_flashcard_repo,
        sample_quiz, sample_questions, sample_attempt, student_id, quiz_id, course_id,
    ):
        mock_repo.get_quiz_by_id.return_value = sample_quiz
        mock_repo.get_questions.return_value = sample_questions
        mock_repo.create_attempt.return_value = sample_attempt
        # All wrong: offset by 1 from correct_index
        wrong_answers = [(q.correct_index + 1) % 4 for q in sample_questions]
        # Make first 3 correct, last 2 wrong
        for i in range(3):
            wrong_answers[i] = sample_questions[i].correct_index
        mock_flashcard_repo.exists_by_source.return_value = False
        mock_flashcard_repo.create.return_value = None  # we don't use the return

        await quiz_service_with_flashcards.submit_quiz(
            quiz_id=quiz_id, student_id=student_id, role="student", answers=wrong_answers,
        )

        assert mock_flashcard_repo.create.await_count == 2
        # Verify flashcard content matches wrong questions
        calls = mock_flashcard_repo.create.call_args_list
        wrong_questions = [sample_questions[3], sample_questions[4]]
        for call, wq in zip(calls, wrong_questions):
            assert call.kwargs["student_id"] == student_id
            assert call.kwargs["course_id"] == sample_quiz.course_id
            assert call.kwargs["concept"] == wq.text
            assert wq.options[wq.correct_index] in call.kwargs["answer"]
            assert call.kwargs["source_type"] == "quiz_mistake"
            assert call.kwargs["source_id"] == wq.id

    async def test_no_duplicate_flashcards(
        self, quiz_service_with_flashcards, mock_repo, mock_flashcard_repo,
        sample_quiz, sample_questions, sample_attempt, student_id, quiz_id,
    ):
        mock_repo.get_quiz_by_id.return_value = sample_quiz
        mock_repo.get_questions.return_value = sample_questions
        mock_repo.create_attempt.return_value = sample_attempt
        # All wrong
        wrong_answers = [(q.correct_index + 1) % 4 for q in sample_questions]
        # Flashcards already exist for all questions
        mock_flashcard_repo.exists_by_source.return_value = True

        await quiz_service_with_flashcards.submit_quiz(
            quiz_id=quiz_id, student_id=student_id, role="student", answers=wrong_answers,
        )

        mock_flashcard_repo.create.assert_not_awaited()

    async def test_all_correct_no_flashcards(
        self, quiz_service_with_flashcards, mock_repo, mock_flashcard_repo,
        sample_quiz, sample_questions, sample_attempt, student_id, quiz_id,
    ):
        mock_repo.get_quiz_by_id.return_value = sample_quiz
        mock_repo.get_questions.return_value = sample_questions
        correct_answers = [q.correct_index for q in sample_questions]
        mock_repo.create_attempt.return_value = sample_attempt

        await quiz_service_with_flashcards.submit_quiz(
            quiz_id=quiz_id, student_id=student_id, role="student", answers=correct_answers,
        )

        mock_flashcard_repo.exists_by_source.assert_not_awaited()
        mock_flashcard_repo.create.assert_not_awaited()


class TestListAttempts:
    async def test_list_my_attempts(
        self, quiz_service, mock_repo, sample_attempt, student_id, quiz_id,
    ):
        mock_repo.list_attempts.return_value = ([sample_attempt], 1)

        attempts, total = await quiz_service.list_my_attempts(quiz_id, student_id)

        assert attempts == [sample_attempt]
        assert total == 1
        mock_repo.list_attempts.assert_awaited_once_with(quiz_id, student_id, 20, 0)
