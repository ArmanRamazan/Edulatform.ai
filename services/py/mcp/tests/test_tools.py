from unittest.mock import AsyncMock, patch

import pytest

from app.client import PlatformClient
from app.tools import register_tools, register_resources


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock(spec=PlatformClient)


class TestToolRegistration:
    def test_register_tools_adds_all_tools(self) -> None:
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        mock = AsyncMock(spec=PlatformClient)
        register_tools(mcp, mock)
        tool_names = {t.name for t in mcp._tool_manager.list_tools()}
        expected = {
            "search_knowledge",
            "search_web",
            "smart_search",
            "get_concept_graph",
            "get_concept",
            "get_mastery",
            "get_daily_summary",
            "get_flashcards_due",
            "start_mission",
            "complete_mission",
            "coach_chat",
            "review_flashcard",
            "create_document",
            "create_concept",
            "update_concept",
            "delete_concept",
            "add_prerequisite",
            # new knowledge tools
            "search_knowledge_base",
            "get_concept_by_name",
            "get_team_mastery",
            "get_user_missions",
            "ask_coach",
        }
        assert tool_names == expected

    def test_all_tools_have_descriptions(self) -> None:
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        mock = AsyncMock(spec=PlatformClient)
        register_tools(mcp, mock)
        for tool in mcp._tool_manager.list_tools():
            assert tool.description, f"Tool {tool.name} has no description"


class TestReadTools:
    async def test_search_knowledge(self, mock_client: AsyncMock) -> None:
        mock_client.search_knowledge.return_value = {"results": [{"title": "Doc1"}]}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "search_knowledge", {"org_id": "org-1", "query": "python"}
        )
        mock_client.search_knowledge.assert_called_once_with("org-1", "python")

    async def test_search_web(self, mock_client: AsyncMock) -> None:
        mock_client.search_external.return_value = {"results": []}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool("search_web", {"query": "asyncio tutorial"})
        mock_client.search_external.assert_called_once_with("asyncio tutorial")

    async def test_smart_search(self, mock_client: AsyncMock) -> None:
        mock_client.search_unified.return_value = {"results": []}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "smart_search", {"org_id": "org-1", "query": "best practices"}
        )
        mock_client.search_unified.assert_called_once_with("org-1", "best practices")

    async def test_get_concept_graph(self, mock_client: AsyncMock) -> None:
        mock_client.get_concept_graph.return_value = {"concepts": []}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool("get_concept_graph", {"org_id": "org-1"})
        mock_client.get_concept_graph.assert_called_once_with("org-1")

    async def test_get_concept(self, mock_client: AsyncMock) -> None:
        mock_client.get_concept.return_value = {"id": "c1", "name": "Python"}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool("get_concept", {"concept_id": "c1"})
        mock_client.get_concept.assert_called_once_with("c1")

    async def test_get_mastery(self, mock_client: AsyncMock) -> None:
        mock_client.get_mastery.return_value = {"levels": []}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool("get_mastery", {})
        mock_client.get_mastery.assert_called_once()

    async def test_get_daily_summary(self, mock_client: AsyncMock) -> None:
        mock_client.get_daily_summary.return_value = {"summary": "ok"}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool("get_daily_summary", {})
        mock_client.get_daily_summary.assert_called_once()

    async def test_get_flashcards_due(self, mock_client: AsyncMock) -> None:
        mock_client.get_flashcards_due.return_value = {"cards": []}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool("get_flashcards_due", {})
        mock_client.get_flashcards_due.assert_called_once()


class TestActionTools:
    async def test_start_mission(self, mock_client: AsyncMock) -> None:
        mock_client.start_mission.return_value = {"session_id": "s1"}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool("start_mission", {"org_id": "org-1"})
        mock_client.start_mission.assert_called_once_with("org-1")

    async def test_complete_mission(self, mock_client: AsyncMock) -> None:
        mock_client.complete_mission.return_value = {"status": "completed"}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "complete_mission",
            {"session_id": "s1", "concept_id": "c1", "org_id": "org-1"},
        )
        mock_client.complete_mission.assert_called_once_with("s1", "c1", "org-1")

    async def test_coach_chat(self, mock_client: AsyncMock) -> None:
        mock_client.coach_chat.return_value = {"reply": "hello"}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "coach_chat", {"session_id": "s1", "message": "help me"}
        )
        mock_client.coach_chat.assert_called_once_with("s1", "help me")

    async def test_review_flashcard(self, mock_client: AsyncMock) -> None:
        mock_client.review_flashcard.return_value = {"next_review": "2026-03-07"}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "review_flashcard", {"card_id": "card-1", "rating": 3}
        )
        mock_client.review_flashcard.assert_called_once_with("card-1", 3)


class TestWriteTools:
    async def test_create_document(self, mock_client: AsyncMock) -> None:
        mock_client.create_document.return_value = {"id": "d1"}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "create_document",
            {"org_id": "org-1", "title": "My Doc", "content": "Hello"},
        )
        mock_client.create_document.assert_called_once_with("org-1", "My Doc", "Hello")

    async def test_create_concept(self, mock_client: AsyncMock) -> None:
        mock_client.create_concept.return_value = {"id": "c1"}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "create_concept",
            {"org_id": "org-1", "name": "Python", "description": "A language"},
        )
        mock_client.create_concept.assert_called_once_with(
            "org-1", "Python", "A language"
        )

    async def test_update_concept(self, mock_client: AsyncMock) -> None:
        mock_client.update_concept.return_value = {"id": "c1"}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "update_concept",
            {"concept_id": "c1", "name": "Python 3", "description": "Updated"},
        )
        mock_client.update_concept.assert_called_once_with("c1", "Python 3", "Updated")

    async def test_delete_concept(self, mock_client: AsyncMock) -> None:
        mock_client.delete_concept.return_value = None
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool("delete_concept", {"concept_id": "c1"})
        mock_client.delete_concept.assert_called_once_with("c1")

    async def test_add_prerequisite(self, mock_client: AsyncMock) -> None:
        mock_client.add_prerequisite.return_value = {"status": "created"}
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "add_prerequisite",
            {"concept_id": "c1", "prerequisite_id": "c2"},
        )
        mock_client.add_prerequisite.assert_called_once_with("c1", "c2")


class TestToolErrorHandling:
    async def test_tool_returns_error_on_client_exception(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.search_knowledge.side_effect = Exception("Connection refused")
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "search_knowledge", {"org_id": "org-1", "query": "test"}
        )
        result_text = str(result)
        assert "error" in result_text.lower()


class TestNewKnowledgeTools:
    async def test_search_knowledge_base(self, mock_client: AsyncMock) -> None:
        mock_client.search_knowledge_base.return_value = {
            "results": [{"title": "Doc", "snippet": "...", "score": 0.9}]
        }
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "search_knowledge_base", {"query": "asyncio patterns", "org_id": "org-1"}
        )
        mock_client.search_knowledge_base.assert_called_once_with("org-1", "asyncio patterns")

    async def test_get_concept_by_name(self, mock_client: AsyncMock) -> None:
        mock_client.get_concept_by_name.return_value = {
            "name": "Python",
            "description": "A language",
            "prerequisites": [],
            "related": [],
        }
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "get_concept_by_name", {"concept_name": "Python", "org_id": "org-1"}
        )
        mock_client.get_concept_by_name.assert_called_once_with("Python", "org-1")

    async def test_get_team_mastery(self, mock_client: AsyncMock) -> None:
        mock_client.get_team_mastery.return_value = {
            "members": [{"user_id": "u1", "score": 0.8}]
        }
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool("get_team_mastery", {"org_id": "org-1"})
        mock_client.get_team_mastery.assert_called_once_with("org-1")

    async def test_get_user_missions(self, mock_client: AsyncMock) -> None:
        mock_client.get_user_missions.return_value = {
            "missions": [{"id": "m1", "status": "active", "title": "Learn Python"}]
        }
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool("get_user_missions", {"user_id": "user-1"})
        mock_client.get_user_missions.assert_called_once()

    async def test_ask_coach(self, mock_client: AsyncMock) -> None:
        mock_client.ask_coach.return_value = {
            "response": "Great question! Here is my advice...",
            "session_id": "s1",
        }
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "ask_coach",
            {"question": "How do I use asyncio?", "context": "Python concurrency"},
        )
        mock_client.ask_coach.assert_called_once_with(
            "How do I use asyncio?", "Python concurrency"
        )

    async def test_search_knowledge_base_returns_error_on_failure(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.search_knowledge_base.side_effect = Exception("Timeout")
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "search_knowledge_base", {"query": "test", "org_id": "org-1"}
        )
        assert "error" in str(result).lower()

    async def test_ask_coach_returns_error_on_failure(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.ask_coach.side_effect = Exception("LLM unavailable")
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        register_tools(mcp, mock_client)
        result = await mcp.call_tool(
            "ask_coach", {"question": "test", "context": "ctx"}
        )
        assert "error" in str(result).lower()


class TestResourceRegistration:
    def test_register_resources_adds_all_resources(self) -> None:
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        mock = AsyncMock(spec=PlatformClient)
        register_resources(mcp, mock)
        templates = mcp._resource_manager.list_templates()
        resources = mcp._resource_manager.list_resources()
        all_uris = {str(r.uri) for r in resources} | {
            str(t.uriTemplate) for t in templates
        }
        expected = {
            "knowledge://graph",
            "progress://daily",
            "progress://mastery",
            "progress://trust-level",
        }
        assert expected.issubset(all_uris)
