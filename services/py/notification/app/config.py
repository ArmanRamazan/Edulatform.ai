from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    learning_service_url: str = "http://localhost:8007/api/learning"
