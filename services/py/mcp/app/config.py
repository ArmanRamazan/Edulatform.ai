from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_base_url: str = "http://localhost:8080"
    auth_token: str = ""

    model_config = {"env_prefix": "MCP_"}


def get_settings() -> Settings:
    return Settings()
