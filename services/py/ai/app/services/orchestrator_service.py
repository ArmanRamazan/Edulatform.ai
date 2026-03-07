from __future__ import annotations

import json
from datetime import date
from uuid import UUID

import httpx
import structlog

from common.errors import AppError
from app.config import Settings
from app.domain.coach import SessionResult
from app.domain.mission import (
    CheckQuestion,
    CodeCase,
    MissionBlueprint,
    RecapQuestion,
)
from app.repositories.cache import AICache
from app.services.designer_service import DesignerService
from app.services.strategist_service import StrategistService

logger = structlog.get_logger()

_DAILY_MISSION_TTL = 86400  # 24 hours
_COMPLETED_CONCEPTS_TTL = 86400 * 30  # 30 days


class AgentOrchestrator:
    def __init__(
        self,
        strategist: StrategistService,
        designer: DesignerService,
        cache: AICache,
        http_client: httpx.AsyncClient,
        settings: Settings,
    ) -> None:
        self._strategist = strategist
        self._designer = designer
        self._cache = cache
        self._http = http_client
        self._settings = settings

    async def get_daily_mission(
        self,
        user_id: UUID,
        org_id: UUID,
        user_profile: dict | None = None,
        mastery_data: list[dict] | None = None,
    ) -> MissionBlueprint:
        today = date.today().isoformat()
        cache_key = f"ai:daily:{user_id}:{today}"

        cached = await self._cache._get(cache_key)
        if cached is not None:
            return self._deserialize_mission(cached)

        concept = await self._strategist.get_next_concept(user_id, org_id)
        if concept is None:
            raise AppError("No concept available for daily mission", status_code=404)

        previous_concepts = await self._load_previous_concepts(user_id)

        mission = await self._designer.design_mission(
            concept_name=concept.name,
            concept_id=concept.concept_id,
            org_id=org_id,
            previous_concepts=previous_concepts[-3:] if previous_concepts else None,
        )

        await self._cache._set(cache_key, self._serialize_mission(mission), _DAILY_MISSION_TTL)

        logger.info(
            "daily_mission_generated",
            user_id=str(user_id),
            concept=concept.name,
        )

        return mission

    async def complete_session(
        self,
        user_id: UUID,
        org_id: UUID,
        session_result: SessionResult,
        concept_id: UUID,
    ) -> dict:
        # Record completed concept
        completed = await self._load_previous_concepts(user_id)
        completed.append(session_result.session_id)
        await self._cache._set(
            f"ai:completed:{user_id}",
            json.dumps(completed),
            _COMPLETED_CONCEPTS_TTL,
        )

        # Adapt learning path
        await self._strategist.adapt_path(
            user_id=user_id,
            org_id=org_id,
            session_result={
                "concept_id": str(concept_id),
                "score": session_result.score / 100.0,
            },
        )

        # Get preview of next concept
        next_concept = await self._strategist.get_next_concept(user_id, org_id)

        return {
            "next_concept_preview": next_concept.name if next_concept else None,
            "total_completed": len(completed),
            "score": session_result.score,
            "mastery_delta": session_result.mastery_delta,
        }

    async def _load_previous_concepts(self, user_id: UUID) -> list[str]:
        raw = await self._cache._get(f"ai:completed:{user_id}")
        if raw is None:
            return []
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _serialize_mission(mission: MissionBlueprint) -> str:
        return json.dumps({
            "concept_name": mission.concept_name,
            "concept_id": str(mission.concept_id),
            "recap_questions": [
                {
                    "question": q.question,
                    "expected_answer": q.expected_answer,
                    "concept_ref": q.concept_ref,
                }
                for q in mission.recap_questions
            ],
            "reading_content": mission.reading_content,
            "check_questions": [
                {
                    "question": q.question,
                    "options": q.options,
                    "correct_index": q.correct_index,
                    "explanation": q.explanation,
                }
                for q in mission.check_questions
            ],
            "code_case": {
                "code_snippet": mission.code_case.code_snippet,
                "language": mission.code_case.language,
                "question": mission.code_case.question,
                "expected_answer": mission.code_case.expected_answer,
                "source_path": mission.code_case.source_path,
            } if mission.code_case else None,
        })

    @staticmethod
    def _deserialize_mission(raw: str) -> MissionBlueprint:
        data = json.loads(raw)
        code_case = None
        if data.get("code_case"):
            cc = data["code_case"]
            code_case = CodeCase(
                code_snippet=cc["code_snippet"],
                language=cc["language"],
                question=cc["question"],
                expected_answer=cc["expected_answer"],
                source_path=cc["source_path"],
            )
        return MissionBlueprint(
            concept_name=data["concept_name"],
            concept_id=UUID(data["concept_id"]),
            recap_questions=[
                RecapQuestion(
                    question=q["question"],
                    expected_answer=q["expected_answer"],
                    concept_ref=q["concept_ref"],
                )
                for q in data.get("recap_questions", [])
            ],
            reading_content=data["reading_content"],
            check_questions=[
                CheckQuestion(
                    question=q["question"],
                    options=q["options"],
                    correct_index=q["correct_index"],
                    explanation=q["explanation"],
                )
                for q in data.get("check_questions", [])
            ],
            code_case=code_case,
        )
