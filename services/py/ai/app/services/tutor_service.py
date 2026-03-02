import logging
import uuid

from common.errors import AppError
from app.config import Settings
from app.domain.models import ChatMessage, TutorChatResponse, TutorFeedbackResponse
from app.repositories.llm_client import GeminiClient
from app.repositories.cache import AICache
from app.services.prompts import TUTOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class TutorService:
    def __init__(self, llm: GeminiClient, cache: AICache, settings: Settings) -> None:
        self._llm = llm
        self._cache = cache
        self._settings = settings

    async def chat(
        self,
        user_id: str,
        lesson_id: str,
        message: str,
        lesson_content: str,
        session_id: str | None = None,
        credits_remaining: int = 0,
    ) -> TutorChatResponse:
        if session_id is None:
            session_id = str(uuid.uuid4())

        history = await self._cache.get_conversation(session_id)

        system_prompt = TUTOR_SYSTEM_PROMPT.format(lesson_content=lesson_content)

        prompt_parts = [system_prompt, ""]
        for msg in history:
            role_label = "Student" if msg["role"] == "user" else "Tutor"
            prompt_parts.append(f"{role_label}: {msg['content']}")
        prompt_parts.append(f"Student: {message}")
        prompt_parts.append("Tutor:")

        full_prompt = "\n".join(prompt_parts)

        raw, tokens_in, tokens_out = await self._llm.generate(full_prompt)
        logger.info(
            "Tutor response: %d tokens in, %d tokens out", tokens_in, tokens_out
        )

        reply = raw.strip()

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": reply})
        await self._cache.save_conversation(
            session_id, history, self._settings.tutor_session_ttl
        )

        return TutorChatResponse(
            session_id=session_id,
            message=reply,
            model_used=self._llm.model_name,
            credits_remaining=credits_remaining,
        )

    async def feedback(
        self,
        session_id: str,
        message_index: int,
        rating: int,
    ) -> TutorFeedbackResponse:
        history = await self._cache.get_conversation(session_id)
        if not history:
            raise AppError("Session not found", status_code=404)

        if message_index >= len(history):
            raise AppError("Invalid message index", status_code=400)

        await self._cache.save_feedback(session_id, message_index, rating)

        return TutorFeedbackResponse(status="ok")
