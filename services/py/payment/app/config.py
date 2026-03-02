from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
