"""Unified search service — orchestrates internal (RAG) and external (LLM) search."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

import httpx
import structlog

from app.config import Settings
from app.domain.unified_search import (
    ExternalSearchResult,
    InternalSearchResult,
    UnifiedSearchResult,
)
from app.repositories.llm_client import GeminiClient
from app.services.query_router import QueryRouter

logger = structlog.get_logger()

_EXTERNAL_SEARCH_PROMPT = """You are a web search assistant. Given the query below, return a JSON array of up to {limit} relevant web resources.

Each item must have: "title", "url", "snippet".
Return ONLY a valid JSON array, no markdown, no extra text.

Query: {query}"""


class UnifiedSearchService:
    """Orchestrates query routing and parallel search execution."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        llm_client: GeminiClient,
        query_router: QueryRouter,
        settings: Settings,
    ) -> None:
        self._http = http_client
        self._llm = llm_client
        self._router = query_router
        self._settings = settings

    async def search(
        self,
        query: str,
        org_id: UUID,
        org_terms: list[str] | None = None,
        limit: int = 5,
    ) -> UnifiedSearchResult:
        if org_terms is None:
            org_terms = []

        route = self._router.classify(query, org_terms)

        internal_results: list[InternalSearchResult] = []
        external_results: list[ExternalSearchResult] = []

        if route == "internal":
            internal_results = await self._search_rag(query, org_id, limit)
        elif route == "external":
            external_results = await self._search_external(query, limit)
        else:
            internal_results, external_results = await asyncio.gather(
                self._search_rag(query, org_id, limit),
                self._search_external(query, limit),
            )

        return UnifiedSearchResult(
            route=route,
            internal_results=internal_results,
            external_results=external_results,
        )

    async def _search_rag(
        self, query: str, org_id: UUID, limit: int,
    ) -> list[InternalSearchResult]:
        url = f"{self._settings.rag_service_url}/kb/{org_id}/search"
        try:
            resp = await self._http.post(
                url,
                json={"query": query, "limit": limit},
                timeout=5.0,
            )
            if resp.status_code != 200:
                logger.warning("rag_search_error", status=resp.status_code)
                return []
            raw = resp.json().get("results", [])
            return [
                InternalSearchResult(
                    title=r.get("document_title", ""),
                    source_path=r.get("source_path", ""),
                    content=r.get("content", ""),
                )
                for r in raw
            ]
        except Exception:
            logger.warning("rag_search_unavailable")
            return []

    async def _search_external(
        self, query: str, limit: int,
    ) -> list[ExternalSearchResult]:
        prompt = _EXTERNAL_SEARCH_PROMPT.format(query=query, limit=limit)
        try:
            text, _, _ = await self._llm.generate(prompt)
            items = json.loads(text)
            if not isinstance(items, list):
                return []
            return [
                ExternalSearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                )
                for item in items
                if isinstance(item, dict)
            ]
        except (json.JSONDecodeError, Exception):
            logger.warning("external_search_failed")
            return []
