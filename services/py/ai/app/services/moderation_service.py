import json

import structlog

from app.domain.models import ModerationResponse
from app.repositories.llm_client import GeminiClient
from app.services.prompts import MODERATION_PROMPT_TEMPLATE

logger = structlog.get_logger()

CRITICAL_FLAGS = frozenset({"inappropriate_content", "hate_speech"})
MAX_CONTENT_LENGTH = 10000

_SAFE_DEFAULT = ModerationResponse(
    approved=True,
    flags=["moderation_unavailable"],
    quality_score=0,
    suggestions=[],
)


class ModerationService:
    def __init__(self, llm: GeminiClient) -> None:
        self._llm = llm

    async def moderate(self, content: str, content_type: str) -> ModerationResponse:
        sanitized = content.strip()[:MAX_CONTENT_LENGTH]

        prompt = MODERATION_PROMPT_TEMPLATE.format(
            content_type=content_type,
            content=sanitized,
        )

        try:
            raw, tokens_in, tokens_out = await self._llm.generate(prompt)
            logger.info("moderation_generated", tokens_in=tokens_in, tokens_out=tokens_out)
        except Exception:
            logger.warning("moderation_llm_failure", exc_info=True)
            return _SAFE_DEFAULT

        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> ModerationResponse:
        text = self._strip_markdown_fences(raw)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("moderation_parse_failure", raw=raw[:200])
            return _SAFE_DEFAULT

        if not isinstance(data, dict) or "quality_score" not in data or "flags" not in data:
            logger.warning("moderation_invalid_structure", data=str(data)[:200])
            return _SAFE_DEFAULT

        quality_score = int(data["quality_score"])
        flags = list(data["flags"])
        suggestions = list(data.get("suggestions", []))

        has_critical = bool(CRITICAL_FLAGS & set(flags))
        approved = quality_score >= 5 and not has_critical

        return ModerationResponse(
            approved=approved,
            flags=flags,
            quality_score=quality_score,
            suggestions=suggestions,
        )

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [line for line in lines if not line.startswith("```")]
            text = "\n".join(lines)
        return text
