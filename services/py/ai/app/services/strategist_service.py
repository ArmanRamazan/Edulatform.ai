from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import httpx
import structlog

from common.errors import AppError
from app.config import Settings
from app.domain.agent import LearningPath, PathConcept
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient

logger = structlog.get_logger()

STRATEGIST_PROMPT_TEMPLATE = """Given this user profile: {user_profile}

And these organization concepts: {concepts_json}

And current mastery levels: {mastery_json}

Create an optimal learning path. Order concepts by:
1. Dependencies (prerequisites first)
2. Priority for the role
3. Current mastery (lowest first)

Return ONLY a JSON array (no markdown fences): [
  {{"concept_id": "uuid", "name": "string", "priority": 1, "estimated_sessions": 3, "prerequisites": ["uuid"]}}
]

Priority scale: 1=critical, 2=important, 3=nice-to-have.
estimated_sessions: number of study sessions needed (1-10)."""


class StrategistService:
    def __init__(
        self,
        gemini_client: GeminiClient,
        cache: AICache,
        http_client: httpx.AsyncClient,
        settings: Settings,
    ) -> None:
        self._llm = gemini_client
        self._cache = cache
        self._http = http_client
        self._settings = settings

    async def plan_path(
        self,
        user_id: UUID,
        org_id: UUID,
        user_profile: dict,
        mastery: list[dict] | None = None,
    ) -> LearningPath:
        concepts = await self._fetch_org_concepts(org_id)
        if not concepts:
            logger.warning("no_org_concepts", org_id=str(org_id))
            return self._empty_path(user_id, org_id)

        mastery_map = self._build_mastery_map(mastery)

        prompt = STRATEGIST_PROMPT_TEMPLATE.format(
            user_profile=json.dumps(user_profile),
            concepts_json=json.dumps(concepts),
            mastery_json=json.dumps(mastery or []),
        )

        raw, tokens_in, tokens_out = await self._llm.generate(prompt)
        logger.info("strategist_path_generated", tokens_in=tokens_in, tokens_out=tokens_out)

        path_concepts = self._parse_path(raw, mastery_map)

        path = LearningPath(
            user_id=user_id,
            organization_id=org_id,
            concepts_ordered=path_concepts,
            current_index=0,
            created_at=datetime.now(timezone.utc),
        )

        cache_key = f"ai:path:{user_id}"
        await self._cache.set_path(cache_key, self._serialize_path(path), self._settings.strategist_path_ttl)

        return path

    async def get_next_concept(
        self,
        user_id: UUID,
        org_id: UUID,
    ) -> PathConcept | None:
        path = await self._load_path(user_id)
        if path is None:
            return None

        for concept in path.concepts_ordered:
            if concept.mastery < 0.7:
                return concept

        return None

    async def adapt_path(
        self,
        user_id: UUID,
        org_id: UUID,
        session_result: dict,
    ) -> LearningPath:
        path = await self._load_path(user_id)
        if path is None:
            raise AppError("No learning path found for user", status_code=404)

        concept_id = session_result["concept_id"]
        score = session_result["score"]
        concepts = list(path.concepts_ordered)

        target_idx = None
        for i, c in enumerate(concepts):
            if str(c.concept_id) == concept_id:
                target_idx = i
                break

        if target_idx is None:
            return path

        target = concepts[target_idx]

        if score < 0.5:
            # Insert prerequisite concepts before the target with boosted priority
            prereq_ids = {str(p) for p in target.prerequisites}
            for i, c in enumerate(concepts):
                if str(c.concept_id) in prereq_ids and i > target_idx:
                    # Move prerequisite before target
                    concepts.pop(i)
                    concepts.insert(target_idx, c)

        elif score > 0.9:
            # Skip remaining sessions for this concept
            concepts[target_idx] = PathConcept(
                concept_id=target.concept_id,
                name=target.name,
                priority=target.priority,
                estimated_sessions=0,
                prerequisites=target.prerequisites,
                mastery=target.mastery,
            )

        updated = LearningPath(
            user_id=path.user_id,
            organization_id=path.organization_id,
            concepts_ordered=concepts,
            current_index=path.current_index,
            created_at=path.created_at,
        )

        cache_key = f"ai:path:{user_id}"
        await self._cache.set_path(cache_key, self._serialize_path(updated), self._settings.strategist_path_ttl)

        return updated

    # --- Private helpers ---

    async def _fetch_org_concepts(self, org_id: UUID) -> list[dict] | None:
        url = f"{self._settings.rag_service_url}/concepts"
        try:
            resp = await self._http.get(url, params={"org_id": str(org_id)}, timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("rag_service_error", status=resp.status_code)
            return None
        except Exception:
            logger.warning("rag_service_unavailable")
            return None

    @staticmethod
    def _build_mastery_map(mastery: list[dict] | None) -> dict[str, float]:
        if not mastery:
            return {}
        return {
            str(c.get("concept_id", "")): c.get("mastery", 0.0)
            for c in mastery
        }

    def _parse_path(self, raw: str, mastery_map: dict[str, float]) -> list[PathConcept]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AppError(f"Failed to parse learning path JSON from LLM: {exc}", status_code=502) from exc

        if not isinstance(data, list):
            raise AppError("LLM returned invalid learning path (expected array)", status_code=502)

        concepts = []
        for item in data:
            cid = str(item["concept_id"])
            concepts.append(PathConcept(
                concept_id=UUID(cid),
                name=item["name"],
                priority=item.get("priority", 2),
                estimated_sessions=item.get("estimated_sessions", 3),
                prerequisites=[UUID(p) for p in item.get("prerequisites", [])],
                mastery=mastery_map.get(cid, 0.0),
            ))
        return concepts

    async def _load_path(self, user_id: UUID) -> LearningPath | None:
        cache_key = f"ai:path:{user_id}"
        raw = await self._cache.get_path(cache_key)
        if raw is None:
            return None
        return self._deserialize_path(raw)

    @staticmethod
    def _serialize_path(path: LearningPath) -> str:
        return json.dumps({
            "user_id": str(path.user_id),
            "organization_id": str(path.organization_id),
            "current_index": path.current_index,
            "created_at": path.created_at.isoformat(),
            "concepts_ordered": [
                {
                    "concept_id": str(c.concept_id),
                    "name": c.name,
                    "priority": c.priority,
                    "estimated_sessions": c.estimated_sessions,
                    "prerequisites": [str(p) for p in c.prerequisites],
                    "mastery": c.mastery,
                }
                for c in path.concepts_ordered
            ],
        })

    @staticmethod
    def _deserialize_path(raw: str) -> LearningPath:
        data = json.loads(raw)
        return LearningPath(
            user_id=UUID(data["user_id"]),
            organization_id=UUID(data["organization_id"]),
            current_index=data["current_index"],
            created_at=datetime.fromisoformat(data["created_at"]),
            concepts_ordered=[
                PathConcept(
                    concept_id=UUID(c["concept_id"]),
                    name=c["name"],
                    priority=c["priority"],
                    estimated_sessions=c["estimated_sessions"],
                    prerequisites=[UUID(p) for p in c["prerequisites"]],
                    mastery=c["mastery"],
                )
                for c in data["concepts_ordered"]
            ],
        )

    @staticmethod
    def _empty_path(user_id: UUID, org_id: UUID) -> LearningPath:
        return LearningPath(
            user_id=user_id,
            organization_id=org_id,
            concepts_ordered=[],
            current_index=0,
            created_at=datetime.now(timezone.utc),
        )
