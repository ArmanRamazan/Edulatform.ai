from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    ai_service_url: str = "http://localhost:8006"
    nats_url: str = "nats://localhost:4222"
