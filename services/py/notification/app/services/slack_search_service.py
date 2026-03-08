from __future__ import annotations

from uuid import UUID

import httpx
import structlog

from common.security import create_access_token

logger = structlog.get_logger()


class SlackSearchService:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        ai_service_url: str,
        jwt_secret: str,
    ) -> None:
        self._http = http_client
        self._ai_base_url = ai_service_url.rstrip("/")
        self._jwt_secret = jwt_secret

    async def search(self, query: str, org_id: UUID | None) -> str:
        """Calls AI unified search, returns formatted text for Slack."""
        try:
            token = self._make_service_token()
            resp = await self._http.post(
                f"{self._ai_base_url}/search",
                json={
                    "query": query,
                    "org_id": str(org_id) if org_id else None,
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return self._format_results(query, results)
        except Exception:
            logger.exception("slack_search_failed", query=query)
            return "Search failed. Please try again later."

    def _format_results(self, query: str, results: list[dict]) -> str:
        if not results:
            return f"No results found for: {query}"
        lines = [f"Results for: {query}", ""]
        for i, item in enumerate(results, start=1):
            title = item.get("title", "Untitled")
            snippet = item.get("snippet", "")
            lines.append(f"{i}. {title} - {snippet}")
        return "\n".join(lines)

    def _make_service_token(self) -> str:
        import uuid
        return create_access_token(
            str(uuid.uuid4()),
            self._jwt_secret,
            extra_claims={"role": "admin", "is_verified": True},
        )
