import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from app.domain.quiz import Quiz, Question, QuizAttempt
from app.repositories.quiz_repo import QuizRepository
from app.services.quiz_service import QuizService


@pytest.fixture
def quiz_id():
    return uuid4()

@pytest.fixture
def lesson_id():
    return uuid4()

@pytest.fixture
def course_id():
    return uuid4()

@pytest.fixture
def teacher_id():
    return uuid4()

@pytest.fixture
def student_id():
    return uuid4()

@pytest.fixture
def sample_quiz(quiz_id, lesson_id, course_id, teacher_id):
    return Quiz(
        id=quiz_id, lesson_id=lesson_id, course_id=course_id,
        teacher_id=teacher_id, created_at=datetime.now(timezone.utc),
    )

@pytest.fixture
def sample_questions(quiz_id):
    return [
        Question(
            id=uuid4(), quiz_id=quiz_id, text=f"Question {i}?",
            options=["A", "B", "C", "D"], correct_index=i % 4,
            explanation=f"Because {i}", order=i,
        )
        for i in range(5)
    ]

@pytest.fixture
def sample_attempt(quiz_id, student_id):
    return QuizAttempt(
        id=uuid4(), quiz_id=quiz_id, student_id=student_id,
        answers=[0, 1, 2, 3, 0], score=0.6,
        completed_at=datetime.now(timezone.utc),
    )

@pytest.fixture
def mock_repo():
    return AsyncMock(spec=QuizRepository)

@pytest.fixture
def quiz_service(mock_repo):
    return QuizService(repo=mock_repo)


@pytest.fixture
def quiz_service_with_flashcards(mock_repo, mock_flashcard_repo):
    return QuizService(repo=mock_repo, flashcard_repo=mock_flashcard_repo)


from app.domain.flashcard import Flashcard, ReviewLog
from app.repositories.flashcard_repo import FlashcardRepository
from app.services.flashcard_service import FlashcardService


@pytest.fixture
def card_id():
    return uuid4()


@pytest.fixture
def sample_flashcard(card_id, student_id, course_id):
    return Flashcard(
        id=card_id, student_id=student_id, course_id=course_id,
        concept="What is Python?", answer="A programming language",
        source_type="manual", source_id=None,
        stability=0.0, difficulty=0.0,
        due=datetime.now(timezone.utc), last_review=None,
        reps=0, lapses=0, state=0,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_review_log(card_id):
    return ReviewLog(
        id=uuid4(), card_id=card_id, rating=3,
        review_duration_ms=5000,
        reviewed_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_flashcard_repo():
    return AsyncMock(spec=FlashcardRepository)


@pytest.fixture
def flashcard_service(mock_flashcard_repo):
    return FlashcardService(repo=mock_flashcard_repo)


from app.domain.concept import Concept
from app.repositories.concept_repo import ConceptRepository
from app.services.concept_service import ConceptService


@pytest.fixture
def concept_id():
    return uuid4()


@pytest.fixture
def sample_concept(concept_id, course_id, lesson_id):
    return Concept(
        id=concept_id, course_id=course_id, lesson_id=lesson_id,
        name="Variables", description="Understanding variables",
        parent_id=None, order=0,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_concept_repo():
    return AsyncMock(spec=ConceptRepository)


@pytest.fixture
def concept_service(mock_concept_repo):
    return ConceptService(repo=mock_concept_repo)


from app.repositories.discussion_repo import DiscussionRepository
from app.services.discussion_service import DiscussionService


@pytest.fixture
def mock_discussion_repo():
    return AsyncMock(spec=DiscussionRepository)


@pytest.fixture
def discussion_service(mock_discussion_repo):
    return DiscussionService(repo=mock_discussion_repo)
