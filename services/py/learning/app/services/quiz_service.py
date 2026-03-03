from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import asyncpg
import structlog

from common.errors import ConflictError, ForbiddenError, NotFoundError
from app.domain.quiz import Quiz, Question, QuizAttempt, QuestionResult
from app.repositories.quiz_repo import QuizRepository

from app.repositories.flashcard_repo import FlashcardRepository

if TYPE_CHECKING:
    from app.services.concept_service import ConceptService

logger = structlog.get_logger()


class QuizService:
    def __init__(
        self,
        repo: QuizRepository,
        concept_service: ConceptService | None = None,
        flashcard_repo: FlashcardRepository | None = None,
    ) -> None:
        self._repo = repo
        self._concept_service = concept_service
        self._flashcard_repo = flashcard_repo

    async def create_quiz(
        self,
        teacher_id: UUID,
        role: str,
        is_verified: bool,
        lesson_id: UUID,
        course_id: UUID,
        questions: list[dict],
    ) -> tuple[Quiz, list[Question]]:
        if role != "teacher" or not is_verified:
            raise ForbiddenError("Only verified teachers can create quizzes")

        try:
            quiz = await self._repo.create_quiz(lesson_id, course_id, teacher_id)
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("Quiz already exists for this lesson") from exc

        question_tuples = [
            (q["text"], q["options"], q["correct_index"], q.get("explanation"), i)
            for i, q in enumerate(questions)
        ]
        created_questions = await self._repo.create_questions(quiz.id, question_tuples)
        return quiz, created_questions

    async def get_quiz_by_lesson(self, lesson_id: UUID) -> tuple[Quiz, list[Question]]:
        quiz = await self._repo.get_quiz_by_lesson(lesson_id)
        if quiz is None:
            raise NotFoundError("No quiz for this lesson")
        questions = await self._repo.get_questions(quiz.id)
        return quiz, questions

    async def submit_quiz(
        self,
        quiz_id: UUID,
        student_id: UUID,
        role: str,
        answers: list[int],
    ) -> tuple[QuizAttempt, list[QuestionResult]]:
        if role != "student":
            raise ForbiddenError("Only students can submit quizzes")

        quiz = await self._repo.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise NotFoundError("Quiz not found")

        questions = await self._repo.get_questions(quiz_id)
        if len(answers) != len(questions):
            raise ValueError(f"Expected {len(questions)} answers, got {len(answers)}")

        results: list[QuestionResult] = []
        correct_count = 0
        for q, selected in zip(questions, answers):
            is_correct = selected == q.correct_index
            if is_correct:
                correct_count += 1
            results.append(QuestionResult(
                question_id=q.id,
                selected=selected,
                correct_index=q.correct_index,
                is_correct=is_correct,
                explanation=q.explanation,
            ))

        score = correct_count / len(questions) if questions else 0.0
        attempt = await self._repo.create_attempt(
            quiz_id=quiz_id, student_id=student_id, answers=answers, score=score,
        )

        if self._concept_service is not None:
            try:
                await self._concept_service.update_mastery_for_lesson(
                    student_id=student_id,
                    lesson_id=quiz.lesson_id,
                    score_delta=score * 0.3,
                )
            except Exception:
                logger.warning("mastery_update_failed", quiz_id=str(quiz_id))

        if self._flashcard_repo is not None:
            await self._generate_flashcards_for_mistakes(
                student_id=student_id,
                course_id=quiz.course_id,
                questions=questions,
                results=results,
            )

        return attempt, results

    async def _generate_flashcards_for_mistakes(
        self,
        student_id: UUID,
        course_id: UUID,
        questions: list[Question],
        results: list[QuestionResult],
    ) -> None:
        assert self._flashcard_repo is not None
        for q, r in zip(questions, results):
            if r.is_correct:
                continue
            try:
                exists = await self._flashcard_repo.exists_by_source(
                    student_id=student_id,
                    source_type="quiz_mistake",
                    source_id=q.id,
                )
                if exists:
                    continue
                correct_answer = q.options[q.correct_index]
                answer = correct_answer
                if q.explanation:
                    answer = f"{correct_answer}. {q.explanation}"
                await self._flashcard_repo.create(
                    student_id=student_id,
                    course_id=course_id,
                    concept=q.text,
                    answer=answer,
                    source_type="quiz_mistake",
                    source_id=q.id,
                )
            except Exception:
                logger.warning("flashcard_create_failed", question_id=str(q.id))

    async def list_my_attempts(
        self, quiz_id: UUID, student_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[QuizAttempt], int]:
        return await self._repo.list_attempts(quiz_id, student_id, limit, offset)
