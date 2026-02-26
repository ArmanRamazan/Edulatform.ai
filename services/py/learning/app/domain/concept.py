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


class MasteryResponse(BaseModel):
    concept_id: UUID
    concept_name: str
    mastery: float


class CourseGraphResponse(BaseModel):
    concepts: list[ConceptResponse]


class CourseMasteryResponse(BaseModel):
    course_id: UUID
    items: list[MasteryResponse]
