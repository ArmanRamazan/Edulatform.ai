from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Concept:
    id: UUID
    course_id: UUID
    lesson_id: UUID | None
    name: str
    description: str
    parent_id: UUID | None
    order: int
    created_at: datetime
    # B2B org-scoping: None for B2C courses, set for org-owned concepts.
    # Source-of-truth for B2B is rag.org_concepts (extracted from docs).
    # learning.concepts is the operational layer (mastery tracking, quiz targets).
    organization_id: UUID | None = None


@dataclass(frozen=True)
class ConceptPrerequisite:
    id: UUID
    concept_id: UUID
    prerequisite_id: UUID


@dataclass(frozen=True)
class ConceptMastery:
    id: UUID
    student_id: UUID
    concept_id: UUID
    mastery: float
    updated_at: datetime


class ConceptCreate(BaseModel):
    course_id: UUID
    lesson_id: UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    parent_id: UUID | None = None
    order: int = Field(default=0, ge=0)
    organization_id: UUID | None = None


class ConceptUpdate(BaseModel):
    lesson_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    parent_id: UUID | None = None
    order: int | None = Field(default=None, ge=0)


class PrerequisiteAdd(BaseModel):
    prerequisite_id: UUID


class ConceptResponse(BaseModel):
    id: UUID
    course_id: UUID
    lesson_id: UUID | None
    name: str
    description: str
    parent_id: UUID | None
    order: int
    created_at: datetime
    prerequisites: list[UUID] = Field(default_factory=list)
    organization_id: UUID | None = None


class MasteryResponse(BaseModel):
    concept_id: UUID
    concept_name: str
    mastery: float


class CourseGraphResponse(BaseModel):
    concepts: list[ConceptResponse]


class CourseMasteryResponse(BaseModel):
    course_id: UUID
    items: list[MasteryResponse]


class MasteryListResponse(BaseModel):
    """Mastery for all (or org-filtered) concepts for a user.

    organization_id is set when filtered to an org; None means unfiltered (B2C behavior).
    """

    items: list[MasteryResponse]
    organization_id: UUID | None = None
