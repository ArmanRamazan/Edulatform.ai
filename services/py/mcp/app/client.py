from typing import Any

import httpx


class PlatformApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


class PlatformClient:
    def __init__(self, base_url: str, token: str) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        kwargs: dict[str, Any] = {}
        if json is not None:
            kwargs["json"] = json
        if params is not None:
            kwargs["params"] = params
        response = await self._http.request(method, path, **kwargs)
        if response.status_code >= 400:
            detail = response.text
            raise PlatformApiError(response.status_code, detail)
        if response.status_code == 204:
            return None
        return response.json()

    async def search_knowledge(self, org_id: str, query: str) -> dict[str, Any]:
        return await self._request("POST", f"/kb/{org_id}/search", json={"query": query})

    async def search_external(self, query: str) -> dict[str, Any]:
        return await self._request("POST", "/ai/search/external", json={"query": query})

    async def search_unified(self, org_id: str, query: str) -> dict[str, Any]:
        return await self._request(
            "POST", "/ai/search/unified", json={"query": query, "org_id": org_id}
        )

    async def get_concept_graph(self, org_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/kb/{org_id}/concepts")

    async def get_concept(self, concept_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/concepts/{concept_id}")

    async def get_mastery(self) -> dict[str, Any]:
        return await self._request("GET", "/concepts/mastery")

    async def get_daily_summary(self) -> dict[str, Any]:
        return await self._request("GET", "/daily/me")

    async def get_flashcards_due(self) -> dict[str, Any]:
        return await self._request("GET", "/flashcards/due")

    async def get_trust_level(self) -> dict[str, Any]:
        return await self._request("GET", "/trust-level/me")

    async def start_mission(self, org_id: str) -> dict[str, Any]:
        return await self._request(
            "GET", "/ai/mission/daily", params={"org_id": org_id}
        )

    async def complete_mission(
        self, session_id: str, concept_id: str, org_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/ai/mission/complete",
            json={"session_id": session_id, "concept_id": concept_id, "org_id": org_id},
        )

    async def coach_chat(self, session_id: str, message: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/ai/coach/chat",
            json={"session_id": session_id, "message": message},
        )

    async def review_flashcard(self, card_id: str, rating: int) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/flashcards/review",
            json={"card_id": card_id, "rating": rating},
        )

    async def create_document(
        self, org_id: str, title: str, content: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/documents",
            json={"org_id": org_id, "title": title, "content": content},
        )

    async def create_concept(
        self, org_id: str, name: str, description: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/concepts",
            json={"org_id": org_id, "name": name, "description": description},
        )

    async def update_concept(
        self, concept_id: str, name: str, description: str
    ) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/concepts/{concept_id}",
            json={"name": name, "description": description},
        )

    async def delete_concept(self, concept_id: str) -> None:
        await self._request("DELETE", f"/concepts/{concept_id}")

    async def add_prerequisite(
        self, concept_id: str, prerequisite_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/concepts/prerequisite",
            json={"concept_id": concept_id, "prerequisite_id": prerequisite_id},
        )

    async def search_knowledge_base(self, org_id: str, query: str) -> dict[str, Any]:
        return await self._request("POST", f"/kb/{org_id}/search", json={"query": query})

    async def get_concept_by_name(self, concept_name: str, org_id: str) -> dict[str, Any]:
        return await self._request(
            "GET", "/concepts", params={"org_id": org_id, "name": concept_name}
        )

    async def get_team_mastery(self, org_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/concepts/mastery/course/{org_id}")

    async def get_user_missions(self) -> dict[str, Any]:
        return await self._request("GET", "/missions/me")

    async def ask_coach(self, question: str, context: str) -> dict[str, Any]:
        return await self._request(
            "POST", "/coach/session", json={"question": question, "context": context}
        )

    async def close(self) -> None:
        await self._http.aclose()
