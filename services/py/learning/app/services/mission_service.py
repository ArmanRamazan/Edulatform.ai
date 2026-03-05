from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

import httpx
import structlog

from common.errors import AppError, ForbiddenError, NotFoundError
from app.domain.mission import Mission
from app.repositories.mission_repo import MissionRepository
from app.services.trust_level_service import TrustLevelService

if TYPE_CHECKING:
    from app.services.review_generator import ReviewGenerator

logger = structlog.get_logger()


class MissionService:
    def __init__(
        self,
        mission_repo: MissionRepository,
        trust_level_service: TrustLevelService,
        http_client: httpx.AsyncClient,
        settings: object,
        review_generator: ReviewGenerator | None = None,
    ) -> None:
        self._repo = mission_repo
        self._trust = trust_level_service
        self._http = http_client
        self._ai_url: str = settings.ai_service_url  # type: ignore[attr-defined]
        self._review_generator = review_generator

    async def get_or_create_today(
        self, user_id: UUID, org_id: UUID, *, token: str,
    ) -> Mission:
        existing = await self._repo.get_today(user_id)
        if existing is not None:
            return existing

        try:
            resp = await self._http.get(
                f"{self._ai_url}/ai/mission/daily",
                params={"org_id": str(org_id)},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            blueprint = resp.json()
        except Exception as exc:
            raise AppError(
                f"AI service error: {exc}", status_code=502,
            ) from exc

        concept_id_raw = blueprint.get("concept_id")
        concept_id = UUID(concept_id_raw) if concept_id_raw else None
        mission_type = blueprint.get("mission_type", "daily")

        return await self._repo.create(
            user_id=user_id,
            organization_id=org_id,
            concept_id=concept_id,
            mission_type=mission_type,
            blueprint=blueprint,
        )

    async def start_mission(self, mission_id: UUID, user_id: UUID) -> Mission:
        mission = await self._repo.get_by_id(mission_id)
        if mission is None:
            raise NotFoundError("Mission not found")
        if mission.user_id != user_id:
            raise ForbiddenError("Not your mission")
        if mission.status != "pending":
            raise AppError("Mission is already started or completed")

        return await self._repo.update_status(
            mission_id,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )

    async def complete_mission(
        self, mission_id: UUID, user_id: UUID, session_id: str, *, token: str,
    ) -> Mission:
        mission = await self._repo.get_by_id(mission_id)
        if mission is None:
            raise NotFoundError("Mission not found")
        if mission.user_id != user_id:
            raise ForbiddenError("Not your mission")
        if mission.status != "in_progress":
            raise AppError("Mission is not in progress")

        try:
            resp = await self._http.post(
                f"{self._ai_url}/ai/coach/end",
                json={"session_id": session_id},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            session_result = resp.json()
        except Exception as exc:
            raise AppError(
                f"Coach service error: {exc}", status_code=502,
            ) from exc

        score = session_result.get("score", 0.0)
        mastery_delta = session_result.get("mastery_delta", 0.0)

        completed = await self._repo.update_status(
            mission_id,
            status="completed",
            score=score,
            mastery_delta=mastery_delta,
            completed_at=datetime.now(timezone.utc),
        )

        await self._trust.record_mission_completed(user_id, mission.organization_id)

        if self._review_generator is not None:
            try:
                await self._review_generator.generate_from_mission(user_id, completed)
            except Exception:
                logger.warning(
                    "review_generation_failed",
                    mission_id=str(mission_id),
                    user_id=str(user_id),
                )

        return completed

    async def get_my_missions(
        self, user_id: UUID, limit: int = 20, offset: int = 0,
    ) -> list[Mission]:
        return await self._repo.get_by_user(user_id, limit, offset)

    async def get_streak(self, user_id: UUID) -> int:
        return await self._repo.get_streak(user_id)
