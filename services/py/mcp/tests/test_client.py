from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.client import PlatformClient


@pytest.fixture
def client() -> PlatformClient:
    return PlatformClient(base_url="http://test:8080", token="test-jwt-token")


class TestPlatformClientInit:
    def test_creates_httpx_client_with_auth_header(self, client: PlatformClient) -> None:
        assert client._http.headers["authorization"] == "Bearer test-jwt-token"

    def test_sets_base_url(self, client: PlatformClient) -> None:
        assert str(client._http.base_url) == "http://test:8080"


class TestSearchKnowledge:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"results": []})
        )
        result = await client.search_knowledge("org-1", "python async")
        client._http.request.assert_called_once_with(
            "POST", "/kb/org-1/search", json={"query": "python async"}
        )
        assert result == {"results": []}

    async def test_raises_on_http_error(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(500, json={"detail": "Internal error"})
        )
        with pytest.raises(Exception, match="500"):
            await client.search_knowledge("org-1", "query")


class TestSearchExternal:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"results": []})
        )
        result = await client.search_external("how to use asyncio")
        client._http.request.assert_called_once_with(
            "POST", "/ai/search/external", json={"query": "how to use asyncio"}
        )
        assert result == {"results": []}


class TestSearchUnified:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"results": []})
        )
        result = await client.search_unified("org-1", "python patterns")
        client._http.request.assert_called_once_with(
            "POST",
            "/ai/search/unified",
            json={"query": "python patterns", "org_id": "org-1"},
        )
        assert result == {"results": []}


class TestGetConceptGraph:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"concepts": []})
        )
        result = await client.get_concept_graph("org-1")
        client._http.request.assert_called_once_with(
            "GET", "/kb/org-1/concepts"
        )
        assert result == {"concepts": []}


class TestGetConcept:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"id": "c1", "name": "Python"})
        )
        result = await client.get_concept("c1")
        client._http.request.assert_called_once_with("GET", "/concepts/c1")
        assert result == {"id": "c1", "name": "Python"}


class TestGetMastery:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"levels": []})
        )
        result = await client.get_mastery()
        client._http.request.assert_called_once_with("GET", "/concepts/mastery")
        assert result == {"levels": []}


class TestGetDailySummary:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"summary": "ok"})
        )
        result = await client.get_daily_summary()
        client._http.request.assert_called_once_with("GET", "/daily/me")
        assert result == {"summary": "ok"}


class TestGetFlashcardsDue:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"cards": []})
        )
        result = await client.get_flashcards_due()
        client._http.request.assert_called_once_with("GET", "/flashcards/due")
        assert result == {"cards": []}


class TestStartMission:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"session_id": "s1"})
        )
        result = await client.start_mission("org-1")
        client._http.request.assert_called_once_with(
            "GET", "/ai/mission/daily", params={"org_id": "org-1"}
        )
        assert result == {"session_id": "s1"}


class TestCompleteMission:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"status": "completed"})
        )
        result = await client.complete_mission("s1", "c1", "org-1")
        client._http.request.assert_called_once_with(
            "POST",
            "/ai/mission/complete",
            json={"session_id": "s1", "concept_id": "c1", "org_id": "org-1"},
        )
        assert result == {"status": "completed"}


class TestCoachChat:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"reply": "hello"})
        )
        result = await client.coach_chat("s1", "explain async")
        client._http.request.assert_called_once_with(
            "POST",
            "/ai/coach/chat",
            json={"session_id": "s1", "message": "explain async"},
        )
        assert result == {"reply": "hello"}


class TestReviewFlashcard:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"next_review": "2026-03-07"})
        )
        result = await client.review_flashcard("card-1", 3)
        client._http.request.assert_called_once_with(
            "POST",
            "/flashcards/review",
            json={"card_id": "card-1", "rating": 3},
        )
        assert result == {"next_review": "2026-03-07"}


class TestCreateDocument:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(201, json={"id": "d1"})
        )
        result = await client.create_document("org-1", "Title", "Content here")
        client._http.request.assert_called_once_with(
            "POST",
            "/documents",
            json={"org_id": "org-1", "title": "Title", "content": "Content here"},
        )
        assert result == {"id": "d1"}


class TestCreateConcept:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(201, json={"id": "c1"})
        )
        result = await client.create_concept("org-1", "Python", "A programming language")
        client._http.request.assert_called_once_with(
            "POST",
            "/concepts",
            json={
                "org_id": "org-1",
                "name": "Python",
                "description": "A programming language",
            },
        )
        assert result == {"id": "c1"}


class TestUpdateConcept:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(200, json={"id": "c1", "name": "Python 3"})
        )
        result = await client.update_concept("c1", "Python 3", "Updated desc")
        client._http.request.assert_called_once_with(
            "PUT",
            "/concepts/c1",
            json={"name": "Python 3", "description": "Updated desc"},
        )
        assert result == {"id": "c1", "name": "Python 3"}


class TestDeleteConcept:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(204, content=b"")
        )
        result = await client.delete_concept("c1")
        client._http.request.assert_called_once_with("DELETE", "/concepts/c1")
        assert result is None


class TestAddPrerequisite:
    async def test_calls_correct_endpoint(self, client: PlatformClient) -> None:
        client._http.request = AsyncMock(
            return_value=httpx.Response(201, json={"status": "created"})
        )
        result = await client.add_prerequisite("c1", "c2")
        client._http.request.assert_called_once_with(
            "POST",
            "/concepts/prerequisite",
            json={"concept_id": "c1", "prerequisite_id": "c2"},
        )
        assert result == {"status": "created"}


class TestClose:
    async def test_closes_http_client(self, client: PlatformClient) -> None:
        client._http.aclose = AsyncMock()
        await client.close()
        client._http.aclose.assert_called_once()
