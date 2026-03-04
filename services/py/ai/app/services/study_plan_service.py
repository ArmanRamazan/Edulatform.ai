import json
from uuid import UUID

import httpx
import structlog

from common.errors import AppError
from app.config import Settings
from app.domain.models import StudyPlanResponse, WeekPlan
from app.repositories.llm_client import GeminiClient
from app.services.prompts import STUDY_PLAN_PROMPT_TEMPLATE, STUDY_PLAN_GENERIC_PROMPT_TEMPLATE

logger = structlog.get_logger()


class StudyPlanService:
    def __init__(self, llm: GeminiClient, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._llm = llm
        self._http = http_client
        self._settings = settings

    async def generate_plan(
        self,
        user_id: UUID,
        course_id: UUID,
        available_hours_per_week: int,
        goal: str | None,
    ) -> StudyPlanResponse:
        mastery_data = await self._fetch_mastery(course_id)
        prompt = self._build_prompt(mastery_data, available_hours_per_week, goal)
        raw, tokens_in, tokens_out = await self._llm.generate(prompt)
        logger.info("study_plan_generated", tokens_in=tokens_in, tokens_out=tokens_out)

        data = self._parse_plan(raw)
        weeks = [WeekPlan(**w) for w in data["weeks"]]

        return StudyPlanResponse(
            weeks=weeks,
            estimated_completion=data.get("estimated_completion", f"{len(weeks)} weeks"),
            total_estimated_hours=data.get(
                "total_estimated_hours",
                round(sum(w.estimated_hours for w in weeks)),
            ),
            model_used=self._llm.model_name,
        )

    async def _fetch_mastery(self, course_id: UUID) -> list[dict] | None:
        url = f"{self._settings.learning_service_url}/concepts/mastery/course/{course_id}"
        try:
            resp = await self._http.get(url, timeout=5.0)
            if resp.status_code == 200:
                return resp.json().get("concepts", [])
            logger.warning("learning_service_error", status=resp.status_code)
            return None
        except Exception:
            logger.warning("learning_service_unavailable")
            return None

    def _build_prompt(
        self,
        mastery_data: list[dict] | None,
        hours: int,
        goal: str | None,
    ) -> str:
        goal_text = goal or "Complete the course efficiently"

        if not mastery_data:
            return STUDY_PLAN_GENERIC_PROMPT_TEMPLATE.format(
                hours=hours,
                goal=goal_text,
            )

        concepts_str = ", ".join(
            f"{c['name']} ({c.get('mastery_level', 0):.0%})"
            for c in mastery_data
        )
        weak = [c["name"] for c in mastery_data if c.get("mastery_level", 0) < 0.5]
        strong = [c["name"] for c in mastery_data if c.get("mastery_level", 0) >= 0.7]

        return STUDY_PLAN_PROMPT_TEMPLATE.format(
            concepts_with_mastery=concepts_str,
            weak_concepts=", ".join(weak) if weak else "None",
            strong_concepts=", ".join(strong) if strong else "None",
            hours=hours,
            goal=goal_text,
        )

    def _parse_plan(self, raw: str) -> dict:
        text = self._strip_markdown_fences(raw)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AppError(f"Failed to parse study plan JSON from LLM: {exc}", status_code=502) from exc

        if not isinstance(data, dict) or "weeks" not in data:
            raise AppError("LLM returned invalid study plan structure (missing 'weeks' key)", status_code=502)

        return data

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.startswith("```")]
            text = "\n".join(lines)
        return text
