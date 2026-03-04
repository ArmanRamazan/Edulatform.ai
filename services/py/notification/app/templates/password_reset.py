"""Password reset email template."""

from __future__ import annotations

from app.templates.base import base_template


def password_reset_email(user_name: str, reset_url: str) -> tuple[str, str]:
    """Generate password reset email.

    Returns:
        Tuple of (subject, html_body).
    """
    subject = "Сброс пароля"
    content = (
        '<h1 style="margin:0 0 16px 0;font-size:22px;color:#111827;">'
        'Здравствуйте, {user_name}!</h1>'
        '<p style="margin:0 0 16px 0;font-size:16px;color:#374151;line-height:1.5;">'
        'Мы получили запрос на сброс пароля для вашего аккаунта. '
        'Нажмите на кнопку ниже, чтобы установить новый пароль.</p>'
        '<div style="text-align:center;margin:24px 0;">'
        '<a href="{reset_url}" style="display:inline-block;padding:14px 32px;'
        'background-color:#2563eb;color:#ffffff;text-decoration:none;'
        'border-radius:6px;font-size:16px;font-weight:bold;">'
        'Сбросить пароль</a></div>'
        '<p style="margin:16px 0 0 0;font-size:14px;color:#6b7280;line-height:1.5;">'
        'Если вы не запрашивали сброс пароля, просто игнорируйте это письмо. '
        'Ваш пароль останется прежним.</p>'
    ).format(user_name=user_name, reset_url=reset_url)
    return subject, base_template(content)
