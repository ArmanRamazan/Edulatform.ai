from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from common.errors import ForbiddenError, NotFoundError


class TestCreateCard:
    async def test_create_card_success(
        self, flashcard_service, mock_flashcard_repo, sample_flashcard, student_id, course_id,
    ):
        mock_flashcard_repo.create.return_value = sample_flashcard

        result = await flashcard_service.create_card(
            student_id=student_id, role="student", course_id=course_id,
            concept="What is Python?", answer="A programming language",
            source_type="manual",
        )

        assert result == sample_flashcard
        mock_flashcard_repo.create.assert_awaited_once_with(
            student_id=student_id, course_id=course_id,
            concept="What is Python?", answer="A programming language",
            source_type="manual", source_id=None,
        )

    async def test_create_card_forbidden_teacher(
        self, flashcard_service, student_id, course_id,
    ):
        with pytest.raises(ForbiddenError):
            await flashcard_service.create_card(
                student_id=student_id, role="teacher", course_id=course_id,
                concept="Q", answer="A",
            )


class TestGetDueCards:
    async def test_get_due_cards_returns_list(
        self, flashcard_service, mock_flashcard_repo, sample_flashcard, student_id,
    ):
        mock_flashcard_repo.get_due_cards.return_value = ([sample_flashcard], 1)

        cards, total = await flashcard_service.get_due_cards(student_id, limit=10, offset=0)

        assert cards == [sample_flashcard]
        assert total == 1
        call_args = mock_flashcard_repo.get_due_cards.call_args
        assert call_args.args[0] == student_id
        assert isinstance(call_args.args[1], datetime)
        assert call_args.args[2] == 10
        assert call_args.args[3] == 0


class TestReviewCard:
    async def test_review_card_success(
        self, flashcard_service, mock_flashcard_repo, sample_flashcard, sample_review_log, card_id, student_id,
    ):
        mock_flashcard_repo.get_by_id.return_value = sample_flashcard
        updated_card = replace(
            sample_flashcard, stability=2.3, difficulty=2.1, reps=1, state=1,
        )
        mock_flashcard_repo.update_fsrs_state.return_value = updated_card
        mock_flashcard_repo.create_review_log.return_value = sample_review_log

        result, info = await flashcard_service.review_card(
            card_id=card_id, student_id=student_id, role="student",
            rating=3, review_duration_ms=5000,
        )

        assert result == updated_card
        assert info["new_stability"] > 0
        assert info["new_difficulty"] > 0
        assert "next_due" in info
        assert "new_state" in info

        update_call = mock_flashcard_repo.update_fsrs_state.call_args
        assert isinstance(update_call.kwargs["stability"], float)
        assert isinstance(update_call.kwargs["difficulty"], float)
        assert update_call.kwargs["stability"] > 0
        # After first Good review on new card, step becomes 1
        assert update_call.kwargs["reps"] == 1

        mock_flashcard_repo.create_review_log.assert_awaited_once_with(
            card_id=card_id, rating=3, review_duration_ms=5000,
        )

    async def test_review_card_not_found(
        self, flashcard_service, mock_flashcard_repo, card_id, student_id,
    ):
        mock_flashcard_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await flashcard_service.review_card(
                card_id=card_id, student_id=student_id, role="student", rating=3,
            )

    async def test_review_card_not_owner(
        self, flashcard_service, mock_flashcard_repo, sample_flashcard, card_id,
    ):
        other_student = uuid4()
        mock_flashcard_repo.get_by_id.return_value = sample_flashcard

        with pytest.raises(ForbiddenError):
            await flashcard_service.review_card(
                card_id=card_id, student_id=other_student, role="student", rating=3,
            )

    async def test_review_card_forbidden_teacher(
        self, flashcard_service, card_id, student_id,
    ):
        with pytest.raises(ForbiddenError):
            await flashcard_service.review_card(
                card_id=card_id, student_id=student_id, role="teacher", rating=3,
            )

    async def test_review_card_again_rating(
        self, flashcard_service, mock_flashcard_repo, sample_flashcard, sample_review_log, card_id, student_id,
    ):
        mock_flashcard_repo.get_by_id.return_value = sample_flashcard
        updated_card = replace(
            sample_flashcard, stability=0.8, difficulty=7.0, reps=0, lapses=0, state=1,
        )
        mock_flashcard_repo.update_fsrs_state.return_value = updated_card
        mock_flashcard_repo.create_review_log.return_value = sample_review_log

        result, info = await flashcard_service.review_card(
            card_id=card_id, student_id=student_id, role="student",
            rating=1,
        )

        assert result == updated_card
        update_call = mock_flashcard_repo.update_fsrs_state.call_args
        # Again on new card keeps state as Learning (1)
        assert update_call.kwargs["state"] == 1
        assert update_call.kwargs["stability"] > 0
        assert update_call.kwargs["reps"] == 0

        mock_flashcard_repo.create_review_log.assert_awaited_once_with(
            card_id=card_id, rating=1, review_duration_ms=None,
        )


class TestDeleteCard:
    async def test_delete_card_success(
        self, flashcard_service, mock_flashcard_repo, card_id, student_id,
    ):
        mock_flashcard_repo.delete.return_value = True

        result = await flashcard_service.delete_card(
            card_id=card_id, student_id=student_id, role="student",
        )

        assert result is True
        mock_flashcard_repo.delete.assert_awaited_once_with(card_id, student_id)

    async def test_delete_card_not_found(
        self, flashcard_service, mock_flashcard_repo, card_id, student_id,
    ):
        mock_flashcard_repo.delete.return_value = False

        with pytest.raises(NotFoundError):
            await flashcard_service.delete_card(
                card_id=card_id, student_id=student_id, role="student",
            )

    async def test_delete_card_forbidden_teacher(
        self, flashcard_service, card_id, student_id,
    ):
        with pytest.raises(ForbiddenError):
            await flashcard_service.delete_card(
                card_id=card_id, student_id=student_id, role="teacher",
            )
