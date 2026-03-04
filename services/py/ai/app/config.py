from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    database_url: str = "postgresql://unused:unused@localhost:5432/unused"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-lite"
    quiz_cache_ttl: int = 86400
    summary_cache_ttl: int = 86400
    tutor_session_ttl: int = 3600
    tutor_daily_limit: int = 10
    learning_service_url: str = "http://localhost:8007"
