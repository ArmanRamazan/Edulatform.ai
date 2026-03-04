from unittest.mock import patch, MagicMock

from common.sentry import setup_sentry, _before_send


class TestSetupSentry:
    def test_empty_dsn_does_nothing(self) -> None:
        with patch("common.sentry.sentry_sdk") as mock_sdk:
            setup_sentry(dsn="", service_name="identity")
            mock_sdk.init.assert_not_called()

    def test_none_dsn_does_nothing(self) -> None:
        with patch("common.sentry.sentry_sdk") as mock_sdk:
            setup_sentry(dsn=None, service_name="identity")
            mock_sdk.init.assert_not_called()

    def test_valid_dsn_calls_init(self) -> None:
        with patch("common.sentry.sentry_sdk") as mock_sdk, \
             patch("common.sentry.FastApiIntegration") as mock_integration:
            setup_sentry(
                dsn="https://key@sentry.io/123",
                service_name="identity",
                environment="staging",
            )
            mock_sdk.init.assert_called_once()
            call_kwargs = mock_sdk.init.call_args[1]
            assert call_kwargs["dsn"] == "https://key@sentry.io/123"
            assert call_kwargs["environment"] == "staging"
            assert call_kwargs["server_name"] == "identity"
            assert call_kwargs["send_default_pii"] is False
            assert call_kwargs["traces_sample_rate"] == 0.1
            assert call_kwargs["profiles_sample_rate"] == 0.1
            assert call_kwargs["before_send"] == _before_send
            assert mock_integration.return_value in call_kwargs["integrations"]

    def test_default_environment_is_production(self) -> None:
        with patch("common.sentry.sentry_sdk") as mock_sdk, \
             patch("common.sentry.FastApiIntegration"):
            setup_sentry(dsn="https://key@sentry.io/123", service_name="test")
            call_kwargs = mock_sdk.init.call_args[1]
            assert call_kwargs["environment"] == "production"


class TestBeforeSend:
    def test_strips_authorization_header(self) -> None:
        event = {
            "request": {
                "headers": {
                    "Authorization": "Bearer secret-token",
                    "Content-Type": "application/json",
                }
            }
        }
        result = _before_send(event, {})
        assert result is not None
        assert "Authorization" not in result["request"]["headers"]
        assert result["request"]["headers"]["Content-Type"] == "application/json"

    def test_strips_cookie_header(self) -> None:
        event = {
            "request": {
                "headers": {
                    "Cookie": "session=abc123",
                    "Accept": "text/html",
                }
            }
        }
        result = _before_send(event, {})
        assert result is not None
        assert "Cookie" not in result["request"]["headers"]
        assert result["request"]["headers"]["Accept"] == "text/html"

    def test_strips_email_from_user_context(self) -> None:
        event = {
            "user": {
                "id": "123",
                "email": "user@example.com",
                "username": "testuser",
            }
        }
        result = _before_send(event, {})
        assert result is not None
        assert "email" not in result["user"]
        assert result["user"]["id"] == "123"
        assert result["user"]["username"] == "testuser"

    def test_strips_phone_from_user_context(self) -> None:
        event = {
            "user": {
                "id": "456",
                "phone": "+1234567890",
            }
        }
        result = _before_send(event, {})
        assert result is not None
        assert "phone" not in result["user"]
        assert result["user"]["id"] == "456"

    def test_handles_event_without_request(self) -> None:
        event = {"message": "test error"}
        result = _before_send(event, {})
        assert result is not None
        assert result["message"] == "test error"

    def test_handles_event_without_user(self) -> None:
        event = {"message": "test error"}
        result = _before_send(event, {})
        assert result is not None
        assert "user" not in result


class TestIdentityServiceSentryConfig:
    def test_settings_have_sentry_fields(self) -> None:
        from app.config import Settings

        settings = Settings(
            database_url="postgresql://localhost/test",
            jwt_secret="test-secret",
        )
        assert settings.sentry_dsn == ""
        assert settings.environment == "production"

    def test_settings_sentry_dsn_from_env(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        import pytest
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("JWT_SECRET", "test-secret")
        monkeypatch.setenv("SENTRY_DSN", "https://key@sentry.io/123")
        monkeypatch.setenv("ENVIRONMENT", "staging")

        from app.config import Settings
        settings = Settings()
        assert settings.sentry_dsn == "https://key@sentry.io/123"
        assert settings.environment == "staging"
