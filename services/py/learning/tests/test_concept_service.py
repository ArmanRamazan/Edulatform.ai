from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from common.errors import ConflictError, ForbiddenError, NotFoundError
from app.domain.concept import Concept, ConceptMastery, ConceptPrerequisite
from datetime import datetime, timezone


class TestCreateConcept:
    async def test_creates_concept_as_verified_teacher(
        self, concept_service, mock_concept_repo, sample_concept, teacher_id, course_id
    ):
        mock_concept_repo.create.return_value = sample_concept

        result = await concept_service.create_concept(
            teacher_id=teacher_id, role="teacher", is_verified=True,
            course_id=course_id, name="Variables",
        )

        assert result.name == "Variables"
        mock_concept_repo.create.assert_called_once()

    async def test_rejects_student(
        self, concept_service, student_id, course_id
    ):
        with pytest.raises(ForbiddenError):
            await concept_service.create_concept(
                teacher_id=student_id, role="student", is_verified=False,
                course_id=course_id, name="Vars",
            )

    async def test_rejects_unverified_teacher(
        self, concept_service, teacher_id, course_id
    ):
        with pytest.raises(ForbiddenError):
            await concept_service.create_concept(
                teacher_id=teacher_id, role="teacher", is_verified=False,
                course_id=course_id, name="Vars",
            )

    async def test_duplicate_name_raises_conflict(
        self, concept_service, mock_concept_repo, teacher_id, course_id
    ):
        mock_concept_repo.create.side_effect = ConflictError("Concept 'Variables' already exists in this course")

        with pytest.raises(ConflictError, match="already exists"):
            await concept_service.create_concept(
                teacher_id=teacher_id, role="teacher", is_verified=True,
                course_id=course_id, name="Variables",
            )


class TestUpdateConcept:
    async def test_updates_concept(
        self, concept_service, mock_concept_repo, sample_concept, concept_id, teacher_id
    ):
        mock_concept_repo.get_by_id.return_value = sample_concept
        updated = Concept(
            id=concept_id, course_id=sample_concept.course_id,
            lesson_id=sample_concept.lesson_id, name="Updated",
            description="New desc", parent_id=None, order=1,
            created_at=sample_concept.created_at,
        )
        mock_concept_repo.update.return_value = updated

        result = await concept_service.update_concept(
            concept_id=concept_id, teacher_id=teacher_id,
            role="teacher", is_verified=True, name="Updated",
        )

        assert result.name == "Updated"

    async def test_not_found_raises(
        self, concept_service, mock_concept_repo, teacher_id
    ):
        mock_concept_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await concept_service.update_concept(
                concept_id=uuid4(), teacher_id=teacher_id,
                role="teacher", is_verified=True, name="X",
            )


class TestDeleteConcept:
    async def test_deletes_concept(
        self, concept_service, mock_concept_repo, concept_id, teacher_id
    ):
        mock_concept_repo.delete.return_value = True

        await concept_service.delete_concept(
            concept_id=concept_id, teacher_id=teacher_id,
            role="teacher", is_verified=True,
        )

        mock_concept_repo.delete.assert_called_once_with(concept_id)

    async def test_not_found_raises(
        self, concept_service, mock_concept_repo, teacher_id
    ):
        mock_concept_repo.delete.return_value = False

        with pytest.raises(NotFoundError):
            await concept_service.delete_concept(
                concept_id=uuid4(), teacher_id=teacher_id,
                role="teacher", is_verified=True,
            )


class TestPrerequisites:
    async def test_add_prerequisite(
        self, concept_service, mock_concept_repo, course_id
    ):
        concept_a = Concept(
            id=uuid4(), course_id=course_id, lesson_id=None,
            name="A", description="", parent_id=None, order=0,
            created_at=datetime.now(timezone.utc),
        )
        concept_b = Concept(
            id=uuid4(), course_id=course_id, lesson_id=None,
            name="B", description="", parent_id=None, order=1,
            created_at=datetime.now(timezone.utc),
        )
        mock_concept_repo.get_by_id.side_effect = [concept_a, concept_b]
        mock_concept_repo.add_prerequisite.return_value = ConceptPrerequisite(
            id=uuid4(), concept_id=concept_a.id, prerequisite_id=concept_b.id,
        )

        await concept_service.add_prerequisite(
            concept_id=concept_a.id, prerequisite_id=concept_b.id,
            role="teacher", is_verified=True,
        )

        mock_concept_repo.add_prerequisite.assert_called_once()

    async def test_cross_course_prerequisite_rejected(
        self, concept_service, mock_concept_repo
    ):
        concept_a = Concept(
            id=uuid4(), course_id=uuid4(), lesson_id=None,
            name="A", description="", parent_id=None, order=0,
            created_at=datetime.now(timezone.utc),
        )
        concept_b = Concept(
            id=uuid4(), course_id=uuid4(), lesson_id=None,
            name="B", description="", parent_id=None, order=0,
            created_at=datetime.now(timezone.utc),
        )
        mock_concept_repo.get_by_id.side_effect = [concept_a, concept_b]

        with pytest.raises(ForbiddenError, match="same course"):
            await concept_service.add_prerequisite(
                concept_id=concept_a.id, prerequisite_id=concept_b.id,
                role="teacher", is_verified=True,
            )


class TestCourseGraph:
    async def test_returns_graph_with_prerequisites(
        self, concept_service, mock_concept_repo, course_id
    ):
        c1_id, c2_id = uuid4(), uuid4()
        concepts = [
            Concept(id=c1_id, course_id=course_id, lesson_id=None,
                    name="A", description="", parent_id=None, order=0,
                    created_at=datetime.now(timezone.utc)),
            Concept(id=c2_id, course_id=course_id, lesson_id=None,
                    name="B", description="", parent_id=None, order=1,
                    created_at=datetime.now(timezone.utc)),
        ]
        mock_concept_repo.get_by_course.return_value = concepts
        mock_concept_repo.get_all_prerequisites.return_value = {c2_id: [c1_id]}

        result = await concept_service.get_course_graph(course_id)

        assert len(result.concepts) == 2
        assert result.concepts[0].prerequisites == []
        assert result.concepts[1].prerequisites == [c1_id]


class TestMastery:
    async def test_get_course_mastery(
        self, concept_service, mock_concept_repo, student_id, course_id, sample_concept
    ):
        mock_concept_repo.get_course_mastery.return_value = [
            (sample_concept, 0.75),
        ]

        result = await concept_service.get_course_mastery(student_id, course_id)

        assert result.course_id == course_id
        assert len(result.items) == 1
        assert result.items[0].mastery == 0.75

    async def test_update_mastery_for_lesson(
        self, concept_service, mock_concept_repo, student_id, lesson_id, sample_concept
    ):
        mock_concept_repo.get_by_lesson.return_value = [sample_concept]
        mock_concept_repo.get_mastery.return_value = ConceptMastery(
            id=uuid4(), student_id=student_id, concept_id=sample_concept.id,
            mastery=0.5, updated_at=datetime.now(timezone.utc),
        )
        mock_concept_repo.upsert_mastery.return_value = ConceptMastery(
            id=uuid4(), student_id=student_id, concept_id=sample_concept.id,
            mastery=0.8, updated_at=datetime.now(timezone.utc),
        )

        await concept_service.update_mastery_for_lesson(student_id, lesson_id, 0.3)

        mock_concept_repo.upsert_mastery.assert_called_once_with(
            student_id, sample_concept.id, 0.8,
        )

    async def test_update_mastery_no_concepts_is_noop(
        self, concept_service, mock_concept_repo, student_id, lesson_id
    ):
        mock_concept_repo.get_by_lesson.return_value = []

        await concept_service.update_mastery_for_lesson(student_id, lesson_id, 0.3)

        mock_concept_repo.upsert_mastery.assert_not_called()
