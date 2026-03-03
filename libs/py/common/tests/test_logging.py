import json
import io
import logging
import os
from unittest.mock import patch

import structlog

from common.logging import configure_logging


def _reset_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()


class TestConfigureLogging:
    def setup_method(self) -> None:
        _reset_logging()

    def teardown_method(self) -> None:
        _reset_logging()

    def test_does_not_raise(self) -> None:
        configure_logging(service_name="test-service")

    def test_json_output_in_production(self) -> None:
        buf = io.StringIO()
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}), \
             patch("sys.stdout", buf):
            configure_logging(service_name="test-service")
            logger = structlog.get_logger()
            logger.info("hello", key="value")

        line = buf.getvalue().strip()
        data = json.loads(line)
        assert data["event"] == "hello"
        assert data["key"] == "value"
        assert data["level"] == "info"
        assert data["service"] == "test-service"
        assert "timestamp" in data

    def test_console_output_in_development(self) -> None:
        buf = io.StringIO()
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}), \
             patch("sys.stderr", buf):
            configure_logging(service_name="test-service")
            logger = structlog.get_logger()
            logger.info("dev_msg")

        output = buf.getvalue()
        assert "dev_msg" in output

    def test_default_log_level(self) -> None:
        buf = io.StringIO()
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}), \
             patch("sys.stdout", buf):
            configure_logging(service_name="test-service", log_level="WARNING")
            logger = structlog.get_logger()
            logger.debug("should_not_appear")

        assert buf.getvalue().strip() == ""
