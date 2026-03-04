"""Email template registry.

Maps notification type strings to template functions.
"""

from __future__ import annotations

from typing import Any

from app.templates.welcome import welcome_email
from app.templates.email_verification import verification_email
from app.templates.password_reset import password_reset_email
from app.templates.enrollment_confirmation import enrollment_email
from app.templates.course_completion import completion_email
from app.templates.review_received import review_email
from app.templates.payout_processed import payout_email

_TEMPLATE_REGISTRY: dict[str, Any] = {
    "welcome": welcome_email,
    "email_verification": verification_email,
    "password_reset": password_reset_email,
    "enrollment_confirmation": enrollment_email,
    "course_completion": completion_email,
    "review_received": review_email,
    "payout_processed": payout_email,
}


def get_email_template(
    notification_type: str, **kwargs: Any
) -> tuple[str, str] | None:
    """Look up and render an email template by notification type.

    Args:
        notification_type: One of the registered template type strings.
        **kwargs: Arguments passed to the template function.

    Returns:
        Tuple of (subject, html_body), or None if type is unknown.
    """
    template_fn = _TEMPLATE_REGISTRY.get(notification_type)
    if template_fn is None:
        return None
    return template_fn(**kwargs)
