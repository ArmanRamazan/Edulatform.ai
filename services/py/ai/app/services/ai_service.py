import json
from uuid import UUID

import structlog

from common.errors import AppError
from app.config import Settings
from app.domain.models import (
    QuestionData, QuizResponse, SummaryResponse,
    CourseOutlineResponse, ModuleOutline, LessonOutline,
)
from app.repositories.llm_client import GeminiClient
from app.repositories.cache import AICache
from app.services.prompts import QUIZ_PROMPT_TEMPLATE, SUMMARY_PROMPT_TEMPLATE, COURSE_OUTLINE_PROMPT_TEMPLATE

logger = structlog.get_logger()


class AIService:
    def __init__(self, llm: GeminiClient, cache: AICache, settings: Settings) -> None:
        self._llm = llm
        self._cache = cache
        self._settings = settings

    async def generate_quiz(self, lesson_id: UUID, content: str) -> QuizResponse:
        cached = await self._cache.get_quiz(lesson_id)
        if cached is not None:
            questions = [QuestionData(**q) for q in json.loads(cached)]
            return QuizResponse(
                lesson_id=lesson_id,
                questions=questions,
                model_used=self._llm.model_name,
                cached=True,
            )

        prompt = QUIZ_PROMPT_TEMPLATE.format(content=content)
        raw, tokens_in, tokens_out = await self._llm.generate(prompt)
        logger.info("quiz_generated", tokens_in=tokens_in, tokens_out=tokens_out)

        questions = self._parse_quiz(raw)
        await self._cache.set_quiz(lesson_id, json.dumps([q.model_dump() for q in questions]), self._settings.quiz_cache_ttl)

        return QuizResponse(
            lesson_id=lesson_id,
            questions=questions,
            model_used=self._llm.model_name,
            cached=False,
        )

    async def generate_summary(self, lesson_id: UUID, content: str) -> SummaryResponse:
        cached = await self._cache.get_summary(lesson_id)
        if cached is not None:
            return SummaryResponse(
                lesson_id=lesson_id,
                summary=cached,
                model_used=self._llm.model_name,
                cached=True,
            )

        prompt = SUMMARY_PROMPT_TEMPLATE.format(content=content)
        raw, tokens_in, tokens_out = await self._llm.generate(prompt)
        logger.info("summary_generated", tokens_in=tokens_in, tokens_out=tokens_out)

        summary = raw.strip()
        await self._cache.set_summary(lesson_id, summary, self._settings.summary_cache_ttl)

        return SummaryResponse(
            lesson_id=lesson_id,
            summary=summary,
            model_used=self._llm.model_name,
            cached=False,
        )

    async def generate_outline(
        self,
        topic: str,
        level: str,
        target_audience: str,
        num_modules: int,
    ) -> CourseOutlineResponse:
        prompt = COURSE_OUTLINE_PROMPT_TEMPLATE.format(
            topic=topic,
            level=level,
            target_audience=target_audience,
            num_modules=num_modules,
        )
        raw, tokens_in, tokens_out = await self._llm.generate(prompt)
        logger.info("outline_generated", tokens_in=tokens_in, tokens_out=tokens_out)

        modules = self._parse_outline(raw)
        total_lessons = sum(len(m.lessons) for m in modules)
        total_minutes = sum(
            lesson.estimated_duration_minutes
            for m in modules
            for lesson in m.lessons
        )
        estimated_hours = max(1, round(total_minutes / 60))

        return CourseOutlineResponse(
            modules=modules,
            total_lessons=total_lessons,
            estimated_duration_hours=estimated_hours,
            model_used=self._llm.model_name,
        )

    def _parse_outline(self, raw: str) -> list[ModuleOutline]:
        text = self._strip_markdown_fences(raw)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AppError(f"Failed to parse outline JSON from LLM: {exc}", status_code=502) from exc

        if not isinstance(data, dict) or "modules" not in data:
            raise AppError("LLM returned invalid outline structure (missing 'modules' key)", status_code=502)

        try:
            return [ModuleOutline(**m) for m in data["modules"]]
        except (TypeError, ValueError) as exc:
            raise AppError(f"Failed to validate outline structure: {exc}", status_code=502) from exc

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.startswith("```")]
            text = "\n".join(lines)
        return text

    def _parse_quiz(self, raw: str) -> list[QuestionData]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            text = "\n".join(lines)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AppError(f"Failed to parse quiz JSON from LLM: {exc}", status_code=502) from exc

        if not isinstance(data, list):
            raise AppError("LLM returned non-array quiz response", status_code=502)

        return [QuestionData(**q) for q in data]
