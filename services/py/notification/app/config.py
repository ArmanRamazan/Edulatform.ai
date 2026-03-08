from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    learning_service_url: str = "http://localhost:8007/api/learning"
    resend_api_key: str = ""
    email_from_address: str = "noreply@eduplatform.ru"
    ws_gateway_url: str = "http://localhost:8011"
    nats_url: str = "nats://localhost:4222"
