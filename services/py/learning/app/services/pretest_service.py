from __future__ import annotations

from uuid import UUID

import structlog

from common.errors import ConflictError, ForbiddenError, NotFoundError
from app.domain.concept import Concept
from app.domain.pretest import PretestAnswer
from app.repositories.pretest_repo import PretestRepository
from app.repositories.concept_repo import ConceptRepository

logger = structlog.get_logger()

MIN_QUESTIONS = 5
MASTERY_CORRECT = 0.7
MASTERY_WRONG = 0.1


def generate_question(concept: Concept) -> tuple[str, str]:
    """Generate a True/False question from concept metadata.

    Returns (question_text, correct_answer).
    """
    return (
        f"True or False: {concept.description}",
        "True",
    )


def pick_next_concept(
    concepts: list[Concept],
    tested_concept_ids: set[UUID],
    last_correct: bool | None,
) -> Concept | None:
    """Adaptive concept selection.

    If last answer was correct → pick concept with highest order (harder).
    If last answer was wrong → pick concept with lowest order (easier).
    If first question (last_correct is None) → pick middle concept.
    Returns None if all concepts tested.
    """
    untested = [c for c in concepts if c.id not in tested_concept_ids]
    if not untested:
        return None

    sorted_concepts = sorted(untested, key=lambda c: c.order)

    if last_correct is None:
        return sorted_concepts[len(sorted_concepts) // 2]
    elif last_correct:
        return sorted_concepts[-1]
    else:
        return sorted_concepts[0]


class PretestService:
    def __init__(
        self,
        pretest_repo: PretestRepository,
        concept_repo: ConceptRepository,
    ) -> None:
        self._pretest_repo = pretest_repo
        self._concept_repo = concept_repo

    async def start_pretest(self, user_id: UUID, course_id: UUID) -> dict:
        existing = await self._pretest_repo.get_by_user_and_course(user_id, course_id)

        if existing is not None:
            if existing.status == "completed":
                raise ConflictError("Pretest for this course already completed")

            # Return current in-progress state
            answers = await self._pretest_repo.get_answers(existing.id)
            concepts = await self._concept_repo.get_by_course(course_id)
            unanswered = [a for a in answers if a.is_correct is None]
            if unanswered:
                current = unanswered[-1]
                return {
                    "pretest_id": existing.id,
                    "question": current.question,
                    "concept_id": current.concept_id,
                    "answer_id": current.id,
                    "total_concepts": len(concepts),
                }
            # All answered but not completed — generate next
            tested_ids = {a.concept_id for a in answers}
            last_correct = answers[-1].is_correct if answers else None
            next_concept = pick_next_concept(concepts, tested_ids, last_correct)
            if next_concept is None:
                raise ConflictError("Pretest for this course already completed")
            question, correct_answer = generate_question(next_concept)
            answer = await self._pretest_repo.add_answer(
                existing.id, next_concept.id, question, correct_answer
            )
            return {
                "pretest_id": existing.id,
                "question": question,
                "concept_id": next_concept.id,
                "answer_id": answer.id,
                "total_concepts": len(concepts),
            }

        concepts = await self._concept_repo.get_by_course(course_id)
        if not concepts:
            raise NotFoundError("No concepts found for this course")

        pretest = await self._pretest_repo.create_pretest(user_id, course_id)
        first_concept = pick_next_concept(concepts, set(), last_correct=None)
        assert first_concept is not None  # guaranteed since concepts is non-empty

        question, correct_answer = generate_question(first_concept)
        answer = await self._pretest_repo.add_answer(
            pretest.id, first_concept.id, question, correct_answer
        )

        return {
            "pretest_id": pretest.id,
            "question": question,
            "concept_id": first_concept.id,
            "answer_id": answer.id,
            "total_concepts": len(concepts),
        }

    async def answer_and_next(
        self, pretest_id: UUID, answer_id: UUID, user_answer: str, user_id: UUID
    ) -> dict:
        pretest = await self._pretest_repo.get_by_id(pretest_id)
        if pretest is None:
            raise NotFoundError("Pretest not found")

        if pretest.user_id != user_id:
            raise ForbiddenError("Not your pretest")

        answers = await self._pretest_repo.get_answers(pretest_id)
        current_answer = next((a for a in answers if a.id == answer_id), None)
        if current_answer is None:
            raise NotFoundError("Answer not found")

        is_correct = user_answer.strip().lower() == current_answer.correct_answer.strip().lower()
        updated = await self._pretest_repo.update_answer(answer_id, user_answer, is_correct)

        # Build set of tested concept ids (including this answer)
        tested_ids = {a.concept_id for a in answers}
        answered_count = sum(1 for a in answers if a.is_correct is not None) + (
            1 if current_answer.is_correct is None else 0
        )

        concepts = await self._concept_repo.get_by_course(pretest.course_id)
        total = len(concepts)

        should_complete = (
            answered_count >= total
            or (answered_count >= MIN_QUESTIONS and answered_count >= total)
            or len(tested_ids) >= total
            or (answered_count >= MIN_QUESTIONS)
        )

        if should_complete:
            return await self._complete_and_return(
                pretest_id, pretest.user_id, pretest.course_id, answers, updated, concepts
            )

        next_concept = pick_next_concept(concepts, tested_ids, last_correct=is_correct)
        if next_concept is None:
            return await self._complete_and_return(
                pretest_id, pretest.user_id, pretest.course_id, answers, updated, concepts
            )

        question, correct_answer = generate_question(next_concept)
        next_answer = await self._pretest_repo.add_answer(
            pretest_id, next_concept.id, question, correct_answer
        )

        return {
            "next_question": question,
            "concept_id": next_concept.id,
            "answer_id": next_answer.id,
            "progress": answered_count / total if total > 0 else 1.0,
            "completed": False,
        }

    async def get_results(self, user_id: UUID, course_id: UUID) -> dict:
        pretest = await self._pretest_repo.get_by_user_and_course(user_id, course_id)
        if pretest is None:
            raise NotFoundError("Pretest not found for this course")

        answers = await self._pretest_repo.get_answers(pretest.id)
        concepts = await self._concept_repo.get_by_course(course_id)

        answer_map: dict[UUID, PretestAnswer] = {a.concept_id: a for a in answers}

        concept_results = []
        total_mastery = 0.0
        for concept in concepts:
            ans = answer_map.get(concept.id)
            if ans is not None and ans.is_correct is not None:
                mastery = MASTERY_CORRECT if ans.is_correct else MASTERY_WRONG
                tested = True
            else:
                mastery = 0.0
                tested = False
            total_mastery += mastery
            concept_results.append({
                "concept_id": concept.id,
                "name": concept.name,
                "mastery": mastery,
                "tested": tested,
            })

        overall = total_mastery / len(concepts) if concepts else 0.0

        return {
            "course_id": course_id,
            "concepts": concept_results,
            "overall_readiness": round(overall, 2),
        }

    async def _complete_and_return(
        self,
        pretest_id: UUID,
        user_id: UUID,
        course_id: UUID,
        previous_answers: list[PretestAnswer],
        current_updated: PretestAnswer,
        concepts: list[Concept],
    ) -> dict:
        # Merge current answer into the list
        all_answers = []
        for a in previous_answers:
            if a.id == current_updated.id:
                all_answers.append(current_updated)
            else:
                all_answers.append(a)

        # Update concept mastery for all answered questions
        for ans in all_answers:
            if ans.is_correct is not None:
                mastery = MASTERY_CORRECT if ans.is_correct else MASTERY_WRONG
                await self._concept_repo.upsert_mastery(user_id, ans.concept_id, mastery)

        await self._pretest_repo.complete_pretest(pretest_id)

        answer_map: dict[UUID, PretestAnswer] = {a.concept_id: a for a in all_answers}
        concept_results = []
        total_mastery = 0.0
        for concept in concepts:
            ans = answer_map.get(concept.id)
            if ans is not None and ans.is_correct is not None:
                mastery = MASTERY_CORRECT if ans.is_correct else MASTERY_WRONG
                tested = True
            else:
                mastery = 0.0
                tested = False
            total_mastery += mastery
            concept_results.append({
                "concept_id": concept.id,
                "name": concept.name,
                "mastery": mastery,
                "tested": tested,
            })

        overall = total_mastery / len(concepts) if concepts else 0.0

        return {
            "completed": True,
            "progress": 1.0,
            "results": {
                "course_id": course_id,
                "concepts": concept_results,
                "overall_readiness": round(overall, 2),
            },
        }
