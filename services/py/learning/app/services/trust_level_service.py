from __future__ import annotations

from uuid import UUID

from app.domain.trust_level import LEVEL_NAMES, LEVEL_THRESHOLDS, TrustLevel
from app.repositories.trust_level_repo import TrustLevelRepository


class TrustLevelService:
    def __init__(self, repo: TrustLevelRepository) -> None:
        self._repo = repo

    async def get_my_level(self, user_id: UUID, org_id: UUID) -> TrustLevel:
        return await self._repo.get_or_create(user_id, org_id)

    async def record_mission_completed(
        self, user_id: UUID, org_id: UUID,
    ) -> TrustLevel:
        await self._repo.get_or_create(user_id, org_id)
        updated = await self._repo.increment_missions(user_id)
        new_level = self.check_level_up(updated)
        if new_level is not None:
            updated = await self._repo.update_level(
                user_id, new_level, updated.unlocked_areas,
            )
        return updated

    async def record_concept_mastered(
        self, user_id: UUID, org_id: UUID,
    ) -> TrustLevel:
        await self._repo.get_or_create(user_id, org_id)
        updated = await self._repo.increment_concepts(user_id)
        new_level = self.check_level_up(updated)
        if new_level is not None:
            updated = await self._repo.update_level(
                user_id, new_level, updated.unlocked_areas,
            )
        return updated

    async def get_org_levels(
        self, org_id: UUID, limit: int = 50, offset: int = 0,
    ) -> list[TrustLevel]:
        return await self._repo.get_by_org(org_id, limit, offset)

    def check_level_up(self, trust_level: TrustLevel) -> int | None:
        """Return the highest achievable level, or None if no level-up."""
        current = trust_level.level
        best = None
        for lvl in range(current + 1, 6):
            threshold = LEVEL_THRESHOLDS[lvl]
            if (
                trust_level.total_missions_completed >= threshold["missions"]
                and trust_level.total_concepts_mastered >= threshold["concepts_mastered"]
            ):
                best = lvl
            else:
                break
        return best
