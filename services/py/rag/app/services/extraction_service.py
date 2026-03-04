from __future__ import annotations

import json
import re
from uuid import UUID

import httpx
import structlog

from app.domain.extraction import ExtractedConcept
from app.repositories.concept_store import ConceptStoreRepository

logger = structlog.get_logger()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

_TEXT_PROMPT = """Extract the key technical concepts from this document.
For each concept return: name, description, related_concepts (list of names).
Return JSON array.

Document:
{content}"""

_CODE_PROMPT = """Extract classes, functions, patterns, and architectural concepts from this {language} code.
For each concept return: name, description, related_concepts (list of names).
Return JSON array.

Code:
{content}"""


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM response."""
    text = text.strip()
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?\s*```$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _parse_concepts(raw_text: str, document_id: UUID) -> list[ExtractedConcept]:
    """Parse JSON concept list from LLM response text."""
    cleaned = _strip_markdown_fences(raw_text)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.warning("extraction_json_parse_failed", raw=raw_text[:200])
        return []

    if not isinstance(data, list):
        return []

    concepts = []
    for item in data:
        if not isinstance(item, dict) or "name" not in item:
            continue
        concepts.append(
            ExtractedConcept(
                name=item["name"],
                description=item.get("description", ""),
                related_concepts=item.get("related_concepts", []),
                source_document_id=document_id,
            )
        )
    return concepts


class ExtractionService:
    def __init__(
        self,
        concept_store: ConceptStoreRepository,
        http_client: httpx.AsyncClient,
        settings: object,
    ) -> None:
        self._store = concept_store
        self._http = http_client
        self._api_key: str = getattr(settings, "openai_api_key", "")

    async def _call_gemini(self, prompt: str) -> str | None:
        """Call Gemini API and return the text response, or None on failure."""
        url = f"{GEMINI_API_URL}/gemini-2.0-flash:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
        }
        params = {"key": self._api_key}

        try:
            resp = await self._http.post(url, json=payload, params=params, timeout=60.0)
            if resp.status_code != 200:
                logger.warning("gemini_extraction_error", status=resp.status_code)
                return None
            body = resp.json()
            return body["candidates"][0]["content"]["parts"][0]["text"]
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            logger.warning("gemini_extraction_failed", error=str(exc))
            return None

    async def extract_concepts(
        self, document_id: UUID, content: str
    ) -> list[ExtractedConcept]:
        prompt = _TEXT_PROMPT.format(content=content[:8000])
        raw = await self._call_gemini(prompt)
        if raw is None:
            return []
        return _parse_concepts(raw, document_id)

    async def extract_from_code(
        self, document_id: UUID, code: str, language: str
    ) -> list[ExtractedConcept]:
        prompt = _CODE_PROMPT.format(content=code[:8000], language=language)
        raw = await self._call_gemini(prompt)
        if raw is None:
            return []
        return _parse_concepts(raw, document_id)

    async def extract_and_store(
        self, org_id: UUID, document_id: UUID, content: str
    ) -> None:
        """Extract concepts from content and store them with relationships."""
        concepts = await self.extract_concepts(document_id, content)
        if not concepts:
            return

        # Upsert all concepts, build name→id map
        name_to_id: dict[str, UUID] = {}
        for concept in concepts:
            cid = await self._store.upsert_concept(
                org_id=org_id,
                name=concept.name,
                description=concept.description,
                source_document_id=document_id,
            )
            name_to_id[concept.name] = cid

        # Create relationships
        for concept in concepts:
            src_id = name_to_id.get(concept.name)
            if src_id is None:
                continue
            for related_name in concept.related_concepts:
                rel_id = name_to_id.get(related_name)
                if rel_id is not None and rel_id != src_id:
                    await self._store.add_relationship(src_id, rel_id, "related")
