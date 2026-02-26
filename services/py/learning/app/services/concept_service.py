from __future__ import annotations

import logging
from uuid import UUID

import asyncpg

from common.errors import ConflictError, ForbiddenError, NotFoundError
from app.domain.concept import (
    Concept,
    ConceptResponse,
    CourseGraphResponse,
    CourseMasteryResponse,
    MasteryResponse,
)
from app.repositories.concept_repo import ConceptRepository

logger = logging.getLogger(__name__)


class ConceptService:
    def __init__(self, repo: ConceptRepository) -> None:
        self._repo = repo

    # --- Teacher CRUD ---

    async def create_concept(
        self,
        teacher_id: UUID,
        role: str,
        is_verified: bool,
        course_id: UUID,
        name: str,
        description: str = "",
        lesson_id: UUID | None = None,
        parent_id: UUID | None = None,
        order: int = 0,
    ) -> Concept:
        if role != "teacher" or not is_verified:
            raise ForbiddenError("Only verified teachers can create concepts")

        try:
            return await self._repo.create(
                course_id=course_id,
                name=name,
                description=description,
                lesson_id=lesson_id,
                parent_id=parent_id,
                order=order,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError(f"Concept '{name}' already exists in this course") from exc

    async def update_concept(
        self,
        concept_id: UUID,
        teacher_id: UUID,
        role: str,
        is_verified: bool,
        **kwargs: object,
    ) -> Concept:
        if role != "teacher" or not is_verified:
            raise ForbiddenError("Only verified teachers can update concepts")

        concept = await self._repo.get_by_id(concept_id)
        if concept is None:
            raise NotFoundError("Concept not found")

        try:
            updated = await self._repo.update(concept_id, **kwargs)
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("Concept with this name already exists in the course") from exc

        if updated is None:
            raise NotFoundError("Concept not found")
        return updated

    async def delete_concept(
        self,
        concept_id: UUID,
        teacher_id: UUID,
        role: str,
        is_verified: bool,
    ) -> None:
        if role != "teacher" or not is_verified:
            raise ForbiddenError("Only verified teachers can delete concepts")

        deleted = await self._repo.delete(concept_id)
        if not deleted:
            raise NotFoundError("Concept not found")

    async def add_prerequisite(
        self,
        concept_id: UUID,
        prerequisite_id: UUID,
        role: str,
        is_verified: bool,
    ) -> None:
        if role != "teacher" or not is_verified:
            raise ForbiddenError("Only verified teachers can manage prerequisites")

        concept = await self._repo.get_by_id(concept_id)
        if concept is None:
            raise NotFoundError("Concept not found")

        prereq = await self._repo.get_by_id(prerequisite_id)
        if prereq is None:
            raise NotFoundError("Prerequisite concept not found")

        if concept.course_id != prereq.course_id:
            raise ForbiddenError("Prerequisites must be in the same course")

        try:
            await self._repo.add_prerequisite(concept_id, prerequisite_id)
        except asyncpg.UniqueViolationError:
            pass  # already exists, idempotent
        except asyncpg.CheckViolationError as exc:
            raise ForbiddenError("A concept cannot be its own prerequisite") from exc

    async def remove_prerequisite(
        self,
        concept_id: UUID,
        prerequisite_id: UUID,
        role: str,
        is_verified: bool,
    ) -> None:
        if role != "teacher" or not is_verified:
            raise ForbiddenError("Only verified teachers can manage prerequisites")

        removed = await self._repo.remove_prerequisite(concept_id, prerequisite_id)
        if not removed:
            raise NotFoundError("Prerequisite link not found")

    # --- Read (any authenticated user) ---

    async def get_course_graph(self, course_id: UUID) -> CourseGraphResponse:
        concepts = await self._repo.get_by_course(course_id)
        prerequisites = await self._repo.get_all_prerequisites(course_id)

        items = [
            ConceptResponse(
                id=c.id,
                course_id=c.course_id,
                lesson_id=c.lesson_id,
                name=c.name,
                description=c.description,
                parent_id=c.parent_id,
                order=c.order,
                created_at=c.created_at,
                prerequisites=prerequisites.get(c.id, []),
            )
            for c in concepts
        ]
        return CourseGraphResponse(concepts=items)

    async def get_course_mastery(
        self, student_id: UUID, course_id: UUID
    ) -> CourseMasteryResponse:
        pairs = await self._repo.get_course_mastery(student_id, course_id)
        items = [
            MasteryResponse(
                concept_id=concept.id,
                concept_name=concept.name,
                mastery=mastery,
            )
            for concept, mastery in pairs
        ]
        return CourseMasteryResponse(course_id=course_id, items=items)

    # --- Mastery updates (called from quiz/flashcard services) ---

    async def update_mastery_for_lesson(
        self, student_id: UUID, lesson_id: UUID, score_delta: float
    ) -> None:
        concepts = await self._repo.get_by_lesson(lesson_id)
        for concept in concepts:
            current = await self._repo.get_mastery(student_id, concept.id)
            current_val = current.mastery if current else 0.0
            new_val = current_val + score_delta
            await self._repo.upsert_mastery(student_id, concept.id, new_val)
            logger.debug(
                "Mastery updated: student=%s concept=%s %.2f -> %.2f",
                student_id, concept.id, current_val, new_val,
            )
