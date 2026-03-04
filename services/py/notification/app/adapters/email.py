from __future__ import annotations

import structlog

logger = structlog.get_logger()


class EmailAdapter:
    """Sends emails by logging to stdout with [EMAIL] prefix.

    In production, this would be replaced with an SMTP/SES adapter.
    """

    async def send(self, to_email: str, subject: str, body: str) -> bool:
        logger.info(
            "[EMAIL] sending",
            to_email=to_email,
            subject=subject,
            body=body,
        )
        return True
