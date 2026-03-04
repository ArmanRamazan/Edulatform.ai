from app.config import Settings
from common.config import BaseAppSettings


def test_settings_inherits_base() -> None:
    assert issubclass(Settings, BaseAppSettings)


def test_settings_defaults(settings: Settings) -> None:
    assert settings.database_url == "postgresql://test:test@localhost:5432/test"
    assert settings.embedding_model == "text-embedding-004"
    assert settings.embedding_dimensions == 768
    assert settings.chunk_size == 1000
    assert settings.chunk_overlap == 200


def test_settings_openai_api_key_default(settings: Settings) -> None:
    assert settings.openai_api_key == ""
