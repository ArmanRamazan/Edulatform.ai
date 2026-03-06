from __future__ import annotations

import asyncio
import json
import random
import re
import time
import uuid
from collections.abc import AsyncGenerator

import structlog

from common.errors import AppError
from app.adapters.ws_client import WsPublisher
from app.config import Settings
from app.domain.coach import CoachMessage, SessionResult
from app.domain.mission import MissionBlueprint
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient

logger = structlog.get_logger()

COACH_SYSTEM_PROMPT = """You are a Coach AI mentoring an engineer through a 15-minute learning session.
Personality: {personality}

Session structure:
Phase 1 (RECAP): Ask 2 quick questions about previous material
Phase 2 (READ): Present reading, ask if anything is unclear
Phase 3 (CHECK): Walk through 3 comprehension questions one by one
Phase 4 (PRACTICE): Present code case, discuss solution
Phase 5 (WRAP-UP): Summarize what was learned, preview tomorrow

Rules:
- Never give answers directly — ask guiding questions (Socratic method)
- If user struggles, break down the question, don't skip it
- Keep responses concise (2-4 sentences)
- Track which phase you're in

MISSION: {concept_name}

RECAP QUESTIONS:
{recap_questions}

READING CONTENT:
{reading_content}

CHECK QUESTIONS:
{check_questions}

CODE CASE:
{code_case}"""

EVALUATION_PROMPT = """Based on this coaching session conversation, evaluate the user's understanding.

Conversation:
{conversation}

Return ONLY valid JSON with this exact structure:
{{"overall_score": <0-100>, "concept_mastery_delta": <0.0-1.0>, "strengths": ["strength1"], "gaps": ["gap1"]}}

Rules:
- overall_score: 0-100 rating of comprehension demonstrated
- concept_mastery_delta: estimated mastery improvement (0.0 to 1.0)
- strengths: list of things the user understood well
- gaps: list of areas that need more work"""


def _strip_markdown_fences(text: str) -> str:
    return re.sub(r"^```(?:json)?\s*\n?|```\s*$", "", text.strip(), flags=re.MULTILINE).strip()


def _format_recap_questions(mission: MissionBlueprint) -> str:
    lines = []
    for i, q in enumerate(mission.recap_questions, 1):
        lines.append(f"{i}. {q.question} (expected: {q.expected_answer})")
    return "\n".join(lines) if lines else "None"


def _format_check_questions(mission: MissionBlueprint) -> str:
    lines = []
    for i, q in enumerate(mission.check_questions, 1):
        options = ", ".join(f"{chr(65+j)}) {o}" for j, o in enumerate(q.options))
        lines.append(f"{i}. {q.question}\n   Options: {options}\n   Correct: {chr(65+q.correct_index)} — {q.explanation}")
    return "\n".join(lines) if lines else "None"


def _format_code_case(mission: MissionBlueprint) -> str:
    if mission.code_case is None:
        return "None"
    cc = mission.code_case
    return f"```{cc.language}\n{cc.code_snippet}\n```\nQuestion: {cc.question}\nExpected: {cc.expected_answer}"


class CoachService:
    def __init__(
        self,
        llm: GeminiClient,
        cache: AICache,
        settings: Settings,
        ws_publisher: WsPublisher | None = None,
    ) -> None:
        self._llm = llm
        self._cache = cache
        self._settings = settings
        self._ws = ws_publisher

    async def _ws_publish(self, user_id: uuid.UUID, message: dict) -> None:
        if self._ws is None:
            return
        try:
            await self._ws.publish_to_user(str(user_id), message)
        except Exception:
            logger.warning("ws_publish_error", user_id=str(user_id), exc_info=True)

    async def start_session(
        self,
        user_id: uuid.UUID,
        mission: MissionBlueprint,
        personality: str = "friendly",
    ) -> CoachMessage:
        session_id = str(uuid.uuid4())

        system_prompt = COACH_SYSTEM_PROMPT.format(
            personality=personality,
            concept_name=mission.concept_name,
            recap_questions=_format_recap_questions(mission),
            reading_content=mission.reading_content,
            check_questions=_format_check_questions(mission),
            code_case=_format_code_case(mission),
        )

        opening_prompt = (
            f"{system_prompt}\n\n"
            "Start Phase 1 (RECAP). Greet the student and ask the first recap question.\n"
            "Coach:"
        )

        raw, tokens_in, tokens_out = await self._llm.generate(opening_prompt)
        logger.info("coach_start", tokens_in=tokens_in, tokens_out=tokens_out)

        reply = raw.strip()

        session_data = {
            "system_prompt": system_prompt,
            "messages": [{"role": "assistant", "content": reply}],
            "phase": "recap",
            "started_at": time.time(),
            "mission": {"concept_name": mission.concept_name},
        }

        await self._cache.save_coach_session(
            session_id, session_data, self._settings.tutor_session_ttl
        )

        result = CoachMessage(
            content=reply,
            phase="recap",
            phase_progress=1,
            session_id=session_id,
        )

        await self._ws_publish(user_id, {
            "type": "coach_message",
            "session_id": session_id,
            "content": reply,
            "phase": "recap",
        })

        return result

    async def chat(
        self,
        user_id: uuid.UUID,
        session_id: str,
        message: str,
    ) -> CoachMessage:
        session_data = await self._cache.get_coach_session(session_id)
        if session_data is None:
            raise AppError("Session not found", status_code=404)

        system_prompt = session_data["system_prompt"]
        messages = session_data["messages"]
        phase = session_data["phase"]

        messages.append({"role": "user", "content": message})

        await self._ws_publish(user_id, {
            "type": "typing_indicator",
            "session_id": session_id,
            "is_typing": True,
        })

        prompt_parts = [system_prompt, ""]
        for msg in messages:
            role_label = "Student" if msg["role"] == "user" else "Coach"
            prompt_parts.append(f"{role_label}: {msg['content']}")
        prompt_parts.append("Coach:")

        full_prompt = "\n".join(prompt_parts)

        raw, tokens_in, tokens_out = await self._llm.generate(full_prompt)
        logger.info("coach_chat", tokens_in=tokens_in, tokens_out=tokens_out)

        reply = raw.strip()
        messages.append({"role": "assistant", "content": reply})

        session_data["messages"] = messages

        await self._cache.save_coach_session(
            session_id, session_data, self._settings.tutor_session_ttl
        )

        user_msg_count = sum(1 for m in messages if m["role"] == "user")

        await self._ws_publish(user_id, {
            "type": "coach_message",
            "session_id": session_id,
            "content": reply,
            "phase": phase,
        })

        return CoachMessage(
            content=reply,
            phase=phase,
            phase_progress=user_msg_count,
            session_id=session_id,
        )

    async def stream_response(
        self,
        session_id: str,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """Yield the coach reply word-by-word as Server-Sent Events.

        Each event: ``data: {"token": "<word>", "done": false}\\n\\n``
        Final event: ``data: {"token": "", "done": true, "full_text": "<reply>"}\\n\\n``
        """
        session_data = await self._cache.get_coach_session(session_id)
        if session_data is None:
            raise AppError("Session not found", status_code=404)

        system_prompt = session_data["system_prompt"]
        messages = session_data["messages"]

        messages.append({"role": "user", "content": message})

        prompt_parts = [system_prompt, ""]
        for msg in messages:
            role_label = "Student" if msg["role"] == "user" else "Coach"
            prompt_parts.append(f"{role_label}: {msg['content']}")
        prompt_parts.append("Coach:")

        full_prompt = "\n".join(prompt_parts)

        raw, tokens_in, tokens_out = await self._llm.generate(full_prompt)
        logger.info("coach_stream", tokens_in=tokens_in, tokens_out=tokens_out)

        reply = raw.strip()

        messages.append({"role": "assistant", "content": reply})
        session_data["messages"] = messages
        await self._cache.save_coach_session(
            session_id, session_data, self._settings.tutor_session_ttl
        )

        for word in reply.split():
            event_data = json.dumps({"token": word, "done": False})
            yield f"data: {event_data}\n\n"
            await asyncio.sleep(random.uniform(0.03, 0.05))  # noqa: S311

        done_data = json.dumps({"token": "", "done": True, "full_text": reply})
        yield f"data: {done_data}\n\n"

    async def end_session(
        self,
        user_id: uuid.UUID,
        session_id: str,
    ) -> SessionResult:
        session_data = await self._cache.get_coach_session(session_id)
        if session_data is None:
            raise AppError("Session not found", status_code=404)

        messages = session_data["messages"]
        started_at = session_data["started_at"]

        conversation_text = "\n".join(
            f"{'Student' if m['role'] == 'user' else 'Coach'}: {m['content']}"
            for m in messages
        )

        eval_prompt = EVALUATION_PROMPT.format(conversation=conversation_text)

        raw, tokens_in, tokens_out = await self._llm.generate(eval_prompt)
        logger.info("coach_eval", tokens_in=tokens_in, tokens_out=tokens_out)

        cleaned = _strip_markdown_fences(raw)
        try:
            evaluation = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as exc:
            raise AppError("Failed to parse evaluation", status_code=502) from exc

        duration = int(time.time() - started_at)

        await self._cache.delete_coach_session(session_id)

        return SessionResult(
            session_id=session_id,
            score=float(evaluation["overall_score"]),
            mastery_delta=float(evaluation["concept_mastery_delta"]),
            duration_seconds=duration,
            strengths=evaluation.get("strengths", []),
            gaps=evaluation.get("gaps", []),
        )
