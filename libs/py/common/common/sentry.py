from typing import Any

import sentry_sdk
import structlog
from sentry_sdk.integrations.fastapi import FastApiIntegration

_SENSITIVE_HEADERS = frozenset({"Authorization", "Cookie"})
_SENSITIVE_USER_FIELDS = frozenset({"email", "phone"})

logger = structlog.get_logger()


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    request = event.get("request")
    if request is not None:
        headers = request.get("headers")
        if headers is not None:
            for header in _SENSITIVE_HEADERS:
                headers.pop(header, None)

    user = event.get("user")
    if user is not None:
        for field in _SENSITIVE_USER_FIELDS:
            user.pop(field, None)

    return event


def setup_sentry(
    dsn: str | None,
    service_name: str,
    environment: str = "production",
) -> None:
    if not dsn:
        logger.info("sentry_disabled", service=service_name)
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
        server_name=service_name,
        integrations=[FastApiIntegration()],
        before_send=_before_send,
    )
    logger.info("sentry_enabled", service=service_name, environment=environment)
