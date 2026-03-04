"""Welcome email template."""

from __future__ import annotations

from app.templates.base import base_template


def welcome_email(user_name: str) -> tuple[str, str]:
    """Generate welcome email for new users.

    Returns:
        Tuple of (subject, html_body).
    """
    subject = "Добро пожаловать в EduPlatform!"
    content = (
        '<h1 style="margin:0 0 16px 0;font-size:22px;color:#111827;">'
        'Привет, {user_name}!</h1>'
        '<p style="margin:0 0 16px 0;font-size:16px;color:#374151;line-height:1.5;">'
        'Добро пожаловать в EduPlatform — вашу платформу для онлайн-обучения.</p>'
        '<p style="margin:0 0 8px 0;font-size:16px;color:#374151;line-height:1.5;">'
        'Что вас ждёт:</p>'
        '<ul style="margin:0 0 24px 0;padding-left:20px;font-size:16px;'
        'color:#374151;line-height:1.8;">'
        '<li>Курсы от лучших преподавателей</li>'
        '<li>Интерактивные тесты и карточки для закрепления</li>'
        '<li>Отслеживание прогресса и достижения</li>'
        '</ul>'
        '<div style="text-align:center;margin:24px 0;">'
        '<a href="#" style="display:inline-block;padding:14px 32px;'
        'background-color:#2563eb;color:#ffffff;text-decoration:none;'
        'border-radius:6px;font-size:16px;font-weight:bold;">'
        'Начать обучение</a></div>'
    ).format(user_name=user_name)
    return subject, base_template(content)
