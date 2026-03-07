import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.client import PlatformClient


def _format_result(data: Any) -> str:
    if data is None:
        return "Done."
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_error(e: Exception) -> str:
    return json.dumps({"error": str(e)}, ensure_ascii=False)


def register_tools(mcp: FastMCP, client: PlatformClient) -> None:
    register_knowledge_tools(mcp, client)
    # --- Read tools ---

    @mcp.tool(name="search_knowledge", description="Search your organization's knowledge base")
    async def search_knowledge(org_id: str, query: str) -> str:
        try:
            result = await client.search_knowledge(org_id, query)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="search_web", description="Search the internet for technical information")
    async def search_web(query: str) -> str:
        try:
            result = await client.search_external(query)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="smart_search", description="AI-routed search across internal KB and web")
    async def smart_search(org_id: str, query: str) -> str:
        try:
            result = await client.search_unified(org_id, query)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="get_concept_graph", description="Get the full concept graph for your organization")
    async def get_concept_graph(org_id: str) -> str:
        try:
            result = await client.get_concept_graph(org_id)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="get_concept", description="Get details about a specific concept")
    async def get_concept(concept_id: str) -> str:
        try:
            result = await client.get_concept(concept_id)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="get_mastery", description="Get your mastery levels across all concepts")
    async def get_mastery() -> str:
        try:
            result = await client.get_mastery()
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="get_daily_summary", description="Get today's learning summary")
    async def get_daily_summary() -> str:
        try:
            result = await client.get_daily_summary()
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="get_flashcards_due", description="Get flashcards due for review")
    async def get_flashcards_due() -> str:
        try:
            result = await client.get_flashcards_due()
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    # --- Action tools ---

    @mcp.tool(name="start_mission", description="Start today's learning mission")
    async def start_mission(org_id: str) -> str:
        try:
            result = await client.start_mission(org_id)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="complete_mission", description="Complete a mission session")
    async def complete_mission(session_id: str, concept_id: str, org_id: str) -> str:
        try:
            result = await client.complete_mission(session_id, concept_id, org_id)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="coach_chat", description="Send a message to the AI coach")
    async def coach_chat(session_id: str, message: str) -> str:
        try:
            result = await client.coach_chat(session_id, message)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="review_flashcard", description="Review a flashcard with difficulty rating (1-4)")
    async def review_flashcard(card_id: str, rating: int) -> str:
        try:
            result = await client.review_flashcard(card_id, rating)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    # --- Write tools ---

    @mcp.tool(name="create_document", description="Upload a document to the knowledge base")
    async def create_document(org_id: str, title: str, content: str) -> str:
        try:
            result = await client.create_document(org_id, title, content)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="create_concept", description="Create a new concept in the knowledge graph")
    async def create_concept(org_id: str, name: str, description: str) -> str:
        try:
            result = await client.create_concept(org_id, name, description)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="update_concept", description="Update an existing concept")
    async def update_concept(concept_id: str, name: str, description: str) -> str:
        try:
            result = await client.update_concept(concept_id, name, description)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="delete_concept", description="Delete a concept from the knowledge graph")
    async def delete_concept(concept_id: str) -> str:
        try:
            result = await client.delete_concept(concept_id)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(name="add_prerequisite", description="Add a prerequisite relationship between concepts")
    async def add_prerequisite(concept_id: str, prerequisite_id: str) -> str:
        try:
            result = await client.add_prerequisite(concept_id, prerequisite_id)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)


def register_knowledge_tools(mcp: FastMCP, client: PlatformClient) -> None:
    @mcp.tool(
        name="search_knowledge_base",
        description="Search the organization knowledge base by natural language query",
    )
    async def search_knowledge_base(query: str, org_id: str) -> str:
        try:
            result = await client.search_knowledge_base(org_id, query)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(
        name="get_concept_by_name",
        description="Look up a concept in the knowledge graph by name within an organization",
    )
    async def get_concept_by_name(concept_name: str, org_id: str) -> str:
        try:
            result = await client.get_concept_by_name(concept_name, org_id)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(
        name="get_team_mastery",
        description="Get per-member mastery levels for all concepts in an organization",
    )
    async def get_team_mastery(org_id: str) -> str:
        try:
            result = await client.get_team_mastery(org_id)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(
        name="get_user_missions",
        description="Get active and completed missions for the authenticated user",
    )
    async def get_user_missions(user_id: str) -> str:
        try:
            result = await client.get_user_missions()
            return _format_result(result)
        except Exception as e:
            return _format_error(e)

    @mcp.tool(
        name="ask_coach",
        description="Ask the AI coach a question with optional context for coaching advice",
    )
    async def ask_coach(question: str, context: str) -> str:
        try:
            result = await client.ask_coach(question, context)
            return _format_result(result)
        except Exception as e:
            return _format_error(e)


def register_resources(mcp: FastMCP, client: PlatformClient) -> None:
    @mcp.resource("knowledge://graph", name="Concept Graph", description="Full concept graph")
    async def concept_graph() -> str:
        result = await client.get_concept_graph("default")
        return _format_result(result)

    @mcp.resource("progress://daily", name="Daily Summary", description="Today's learning summary")
    async def daily_summary() -> str:
        result = await client.get_daily_summary()
        return _format_result(result)

    @mcp.resource("progress://mastery", name="Mastery Levels", description="All mastery levels")
    async def mastery_levels() -> str:
        result = await client.get_mastery()
        return _format_result(result)

    @mcp.resource("progress://trust-level", name="Trust Level", description="Current trust level")
    async def trust_level() -> str:
        result = await client.get_trust_level()
        return _format_result(result)
