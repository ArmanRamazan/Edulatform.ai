from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    jwt_ttl_seconds: int = 3600
    refresh_token_ttl_days: int = 30
    sentry_dsn: str = ""
    environment: str = "production"
