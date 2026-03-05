from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    ai_service_url: str = "http://localhost:8006"
