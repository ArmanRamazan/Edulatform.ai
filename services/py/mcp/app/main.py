from mcp.server.fastmcp import FastMCP

from app.client import PlatformClient
from app.config import get_settings
from app.tools import register_resources, register_tools

settings = get_settings()
client = PlatformClient(base_url=settings.api_base_url, token=settings.auth_token)
mcp = FastMCP("KnowledgeOS", json_response=True)

register_tools(mcp, client)
register_resources(mcp, client)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
