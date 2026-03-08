from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from common.errors import ConflictError, ForbiddenError, NotFoundError
from common.nats import NATSClient

if TYPE_CHECKING:
    from app.services.activity_service import ActivityService
from app.domain.concept import (
    Concept,
    ConceptResponse,
    CourseGraphResponse,
    CourseMasteryResponse,
    MasteryListResponse,
    MasteryResponse,
)
from app.domain.events import MasteryUpdated
from app.repositories.concept_repo import ConceptRepository

logger = structlog.get_logger()


class ConceptService:
    """Manage learning concepts (knowledge graph nodes) and mastery tracking.

    Concept model:
        learning.concepts  — operational layer: mastery tracking, quiz targets,
                             knowledge graph edges (prerequisites).
                             B2C: course_id/lesson_id set, organization_id=None.
                             B2B: organization_id set for org-scoped concepts.
        rag.org_concepts   — source-of-truth for B2B: extracted from ingested docs.
                             Future: sync rag → learning on document ingestion event.

    Do NOT merge the tables; they serve different layers.
    """

    def __init__(
        self,
        repo: ConceptRepository,
        activity_service: ActivityService | None = None,
        nats_client: NATSClient | None = None,
    ) -> None:
        self._repo = repo
        self._activity_service = activity_service
        self._nats_client = nats_client

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
        organization_id: UUID | None = None,
    ) -> Concept:
        if role != "teacher" or not is_verified:
            raise ForbiddenError("Only verified teachers can create concepts")

        return await self._repo.create(
            course_id=course_id,
            name=name,
            description=description,
            lesson_id=lesson_id,
            parent_id=parent_id,
            order=order,
            organization_id=organization_id,
        )

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

        updated = await self._repo.update(concept_id, **kwargs)

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
        except ConflictError:
            pass  # already exists, idempotent

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

    async def list_concepts(self, org_id: UUID | None = None) -> list[Concept]:
        """List concepts, optionally filtered to an organization.

        B2B: pass org_id to get org-scoped concepts.
        B2C: pass None to return all concepts (no org filter).
        """
        return await self._repo.list_concepts(org_id=org_id)

    async def get_user_mastery(
        self, student_id: UUID, org_id: UUID | None = None
    ) -> MasteryListResponse:
        """Get mastery for a user, optionally scoped to an organization's concepts.

        B2B: pass org_id — returns all org concepts with mastery (0.0 default).
        B2C: pass None — returns only concepts where the student has explicit mastery records.
        """
        pairs = await self._repo.get_user_mastery(student_id, org_id=org_id)
        items = [
            MasteryResponse(
                concept_id=concept.id,
                concept_name=concept.name,
                mastery=mastery,
            )
            for concept, mastery in pairs
        ]
        return MasteryListResponse(items=items, organization_id=org_id)

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

    # --- Mastery updates (called from quiz/flashcard/mission services) ---

    async def apply_mastery_delta(
        self,
        student_id: UUID,
        concept_id: UUID,
        delta: float,
        organization_id: str | None = None,
    ) -> None:
        """Apply a mastery delta to a specific concept. Called by MissionService after completion.

        After persisting the update, publishes a MasteryUpdated event to NATS
        (subject: platform.mastery.updated) if a NATSClient is configured.
        NATS publish errors are logged and swallowed — mastery persistence takes priority.
        """
        current = await self._repo.get_mastery(student_id, concept_id)
        current_val = current.mastery if current else 0.0
        new_val = current_val + delta
        await self._repo.upsert_mastery(student_id, concept_id, new_val)
        logger.debug(
            "mission_mastery_updated",
            student_id=str(student_id),
            concept_id=str(concept_id),
            old_value=current_val,
            new_value=new_val,
        )

        if self._nats_client is not None:
            event = MasteryUpdated(
                user_id=str(student_id),
                organization_id=organization_id or "",
                concept_id=str(concept_id),
                new_level=new_val,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            try:
                payload = json.dumps(dataclasses.asdict(event)).encode()
                await self._nats_client.publish("platform.mastery.updated", payload)
            except Exception:
                logger.warning(
                    "mastery_event_publish_failed",
                    student_id=str(student_id),
                    concept_id=str(concept_id),
                )

    async def update_mastery_for_lesson(
        self, student_id: UUID, lesson_id: UUID, score_delta: float
    ) -> None:
        concepts = await self._repo.get_by_lesson(lesson_id)
        for concept in concepts:
            current = await self._repo.get_mastery(student_id, concept.id)
            current_val = current.mastery if current else 0.0
            new_val = current_val + score_delta
            await self._repo.upsert_mastery(student_id, concept.id, new_val)
            logger.debug("mastery_updated", student_id=str(student_id), concept_id=str(concept.id), old_value=current_val, new_value=new_val)

            if new_val >= 1.0 and current_val < 1.0 and self._activity_service is not None:
                try:
                    from app.domain.activity import ActivityType
                    await self._activity_service.record(
                        user_id=student_id,
                        activity_type=ActivityType.concept_mastered,
                        payload={"concept_id": str(concept.id), "concept_name": concept.name},
                    )
                except Exception:
                    logger.warning("activity_record_failed", concept_id=str(concept.id))
