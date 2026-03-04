"""Course completion email template."""

from __future__ import annotations

from app.templates.base import base_template


def completion_email(user_name: str, course_title: str) -> tuple[str, str]:
    """Generate course completion congratulations email.

    Returns:
        Tuple of (subject, html_body).
    """
    subject = "Поздравляем! Курс завершён"
    content = (
        '<h1 style="margin:0 0 16px 0;font-size:22px;color:#111827;">'
        'Поздравляем, {user_name}! 🎉</h1>'
        '<p style="margin:0 0 16px 0;font-size:16px;color:#374151;line-height:1.5;">'
        'Вы успешно завершили курс <strong>{course_title}</strong>.</p>'
        '<p style="margin:0 0 16px 0;font-size:16px;color:#374151;line-height:1.5;">'
        'Это отличное достижение! Продолжайте учиться — '
        'впереди ещё много интересного.</p>'
        '<p style="margin:0 0 0 0;font-size:16px;color:#374151;line-height:1.5;">'
        'Посмотрите другие курсы на платформе, чтобы продолжить обучение.</p>'
    ).format(user_name=user_name, course_title=course_title)
    return subject, base_template(content)
