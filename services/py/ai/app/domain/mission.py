from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RecapQuestion:
    question: str
    expected_answer: str
    concept_ref: str


@dataclass(frozen=True)
class CheckQuestion:
    question: str
    options: list[str]
    correct_index: int
    explanation: str


@dataclass(frozen=True)
class CodeCase:
    code_snippet: str
    language: str
    question: str
    expected_answer: str
    source_path: str


@dataclass(frozen=True)
class MissionBlueprint:
    concept_name: str
    concept_id: UUID
    recap_questions: list[RecapQuestion]
    reading_content: str
    check_questions: list[CheckQuestion]
    code_case: CodeCase | None
