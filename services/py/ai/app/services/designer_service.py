from __future__ import annotations

import json
from uuid import UUID

import httpx
import structlog

from common.errors import AppError
from app.config import Settings
from app.domain.mission import (
    CheckQuestion,
    CodeCase,
    MissionBlueprint,
    RecapQuestion,
)
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient

logger = structlog.get_logger()

READING_PROMPT_TEMPLATE = """Create a 2-minute technical reading (~400 words) about {concept_name}.

Use ONLY the following source materials as your foundation — do not invent information:

{source_materials}

Target audience: experienced engineer, new to this codebase.
Include code examples from the sources where relevant.
Write in clear, concise technical prose. No markdown headers."""

CHECK_QUESTIONS_PROMPT_TEMPLATE = """Generate 3 multiple-choice questions testing understanding of {concept_name}.

Base questions ONLY on this material:
{reading_content}

Return ONLY a JSON array (no markdown fences):
[{{"question": "...", "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "..."}}]

Each question must have exactly 4 options and one correct answer."""

CODE_CASE_PROMPT_TEMPLATE = """Generate a practical code analysis task from this real codebase code:

{code_snippets}

Source files: {source_paths}

Ask the engineer to identify a bug, explain a pattern, or predict behavior.
Return ONLY JSON (no markdown fences):
{{"code_snippet": "...", "language": "...", "question": "...", "expected_answer": "...", "source_path": "..."}}

The source_path must be one of the provided source files."""

RECAP_PROMPT_TEMPLATE = """Generate 2 spaced-repetition recap questions about {concepts}.

Use this source material:
{source_materials}

Return ONLY a JSON array (no markdown fences):
[{{"question": "...", "expected_answer": "...", "concept_ref": "..."}}]

Keep questions concise and focused on key concepts. concept_ref should be the concept name."""


class DesignerService:
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

    async def design_mission(
        self,
        concept_name: str,
        concept_id: UUID,
        org_id: UUID,
        previous_concepts: list[str] | None = None,
    ) -> MissionBlueprint:
        rag_results = await self._search_rag(concept_name, org_id, limit=10)

        source_materials = self._format_sources(rag_results)
        code_sources = self._extract_code_sources(rag_results)

        reading_content = await self._generate_reading(concept_name, source_materials)
        check_questions = await self._generate_check_questions(concept_name, reading_content)
        code_case = await self._generate_code_case(code_sources) if code_sources else None

        recap_questions: list[RecapQuestion] = []
        if previous_concepts:
            recap_questions = await self._generate_recap(previous_concepts, org_id)

        return MissionBlueprint(
            concept_name=concept_name,
            concept_id=concept_id,
            recap_questions=recap_questions,
            reading_content=reading_content,
            check_questions=check_questions,
            code_case=code_case,
        )

    async def _search_rag(self, query: str, org_id: UUID, limit: int = 5) -> list[dict]:
        url = f"{self._settings.rag_service_url}/search"
        try:
            resp = await self._http.post(
                url,
                json={"query": query, "org_id": str(org_id), "limit": limit},
                timeout=5.0,
            )
            if resp.status_code == 200:
                return resp.json().get("results", [])
            logger.warning("rag_search_error", status=resp.status_code)
            return []
        except Exception:
            logger.warning("rag_search_unavailable")
            return []

    async def _generate_reading(self, concept_name: str, source_materials: str) -> str:
        prompt = READING_PROMPT_TEMPLATE.format(
            concept_name=concept_name,
            source_materials=source_materials,
        )
        raw, tokens_in, tokens_out = await self._llm.generate(prompt)
        logger.info("designer_reading_generated", tokens_in=tokens_in, tokens_out=tokens_out)
        return raw

    async def _generate_check_questions(self, concept_name: str, reading_content: str) -> list[CheckQuestion]:
        prompt = CHECK_QUESTIONS_PROMPT_TEMPLATE.format(
            concept_name=concept_name,
            reading_content=reading_content,
        )
        raw, tokens_in, tokens_out = await self._llm.generate(prompt)
        logger.info("designer_check_questions_generated", tokens_in=tokens_in, tokens_out=tokens_out)
        return self._parse_check_questions(raw)

    async def _generate_code_case(self, code_sources: list[dict]) -> CodeCase | None:
        snippets = "\n\n---\n\n".join(
            f"File: {s['source_path']}\n```\n{s['content']}\n```"
            for s in code_sources
        )
        source_paths = ", ".join(s["source_path"] for s in code_sources)

        prompt = CODE_CASE_PROMPT_TEMPLATE.format(
            code_snippets=snippets,
            source_paths=source_paths,
        )
        raw, tokens_in, tokens_out = await self._llm.generate(prompt)
        logger.info("designer_code_case_generated", tokens_in=tokens_in, tokens_out=tokens_out)
        return self._parse_code_case(raw)

    async def _generate_recap(
        self,
        previous_concepts: list[str],
        org_id: UUID,
    ) -> list[RecapQuestion]:
        all_sources = []
        for concept in previous_concepts:
            results = await self._search_rag(concept, org_id, limit=3)
            all_sources.extend(results)

        source_materials = self._format_sources(all_sources)
        concepts_str = ", ".join(previous_concepts)

        prompt = RECAP_PROMPT_TEMPLATE.format(
            concepts=concepts_str,
            source_materials=source_materials,
        )
        raw, tokens_in, tokens_out = await self._llm.generate(prompt)
        logger.info("designer_recap_generated", tokens_in=tokens_in, tokens_out=tokens_out)
        return self._parse_recap_questions(raw)

    @staticmethod
    def _format_sources(results: list[dict]) -> str:
        if not results:
            return "(No source materials available)"
        parts = []
        for r in results:
            title = r.get("document_title", "Unknown")
            path = r.get("source_path", "")
            content = r.get("content", "")
            parts.append(f"[{title}] ({path}):\n{content}")
        return "\n\n".join(parts)

    @staticmethod
    def _extract_code_sources(results: list[dict]) -> list[dict]:
        code_extensions = (".py", ".rs", ".ts", ".tsx", ".js", ".jsx")
        return [
            r for r in results
            if r.get("source_path", "").endswith(code_extensions)
        ]

    def _parse_check_questions(self, raw: str) -> list[CheckQuestion]:
        text = self._strip_markdown_fences(raw)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AppError(f"Failed to parse check questions JSON: {exc}", status_code=502) from exc

        if not isinstance(data, list):
            raise AppError("LLM returned invalid check questions (expected array)", status_code=502)

        return [
            CheckQuestion(
                question=item["question"],
                options=item["options"],
                correct_index=item["correct_index"],
                explanation=item["explanation"],
            )
            for item in data
        ]

    def _parse_code_case(self, raw: str) -> CodeCase | None:
        text = self._strip_markdown_fences(raw)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("designer_code_case_parse_failed")
            return None

        if not isinstance(data, dict):
            return None

        return CodeCase(
            code_snippet=data["code_snippet"],
            language=data["language"],
            question=data["question"],
            expected_answer=data["expected_answer"],
            source_path=data["source_path"],
        )

    def _parse_recap_questions(self, raw: str) -> list[RecapQuestion]:
        text = self._strip_markdown_fences(raw)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AppError(f"Failed to parse recap questions JSON: {exc}", status_code=502) from exc

        if not isinstance(data, list):
            raise AppError("LLM returned invalid recap questions (expected array)", status_code=502)

        return [
            RecapQuestion(
                question=item["question"],
                expected_answer=item["expected_answer"],
                concept_ref=item["concept_ref"],
            )
            for item in data
        ]

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.startswith("```")]
            text = "\n".join(lines)
        return text
