"""Email verification template."""

from __future__ import annotations

from app.templates.base import base_template


def verification_email(user_name: str, verify_url: str) -> tuple[str, str]:
    """Generate email verification message.

    Returns:
        Tuple of (subject, html_body).
    """
    subject = "Подтвердите email"
    content = (
        '<h1 style="margin:0 0 16px 0;font-size:22px;color:#111827;">'
        'Здравствуйте, {user_name}!</h1>'
        '<p style="margin:0 0 16px 0;font-size:16px;color:#374151;line-height:1.5;">'
        'Для завершения регистрации подтвердите ваш email-адрес, '
        'нажав на кнопку ниже.</p>'
        '<div style="text-align:center;margin:24px 0;">'
        '<a href="{verify_url}" style="display:inline-block;padding:14px 32px;'
        'background-color:#2563eb;color:#ffffff;text-decoration:none;'
        'border-radius:6px;font-size:16px;font-weight:bold;">'
        'Подтвердить email</a></div>'
        '<p style="margin:16px 0 0 0;font-size:14px;color:#6b7280;line-height:1.5;">'
        'Ссылка действительна в течение 24 часов. '
        'Если вы не регистрировались на EduPlatform, проигнорируйте это письмо.</p>'
    ).format(user_name=user_name, verify_url=verify_url)
    return subject, base_template(content)
