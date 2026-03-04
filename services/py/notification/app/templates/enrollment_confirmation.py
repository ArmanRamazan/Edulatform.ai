"""Enrollment confirmation email template."""

from __future__ import annotations

from app.templates.base import base_template


def enrollment_email(
    user_name: str, course_title: str, course_url: str
) -> tuple[str, str]:
    """Generate enrollment confirmation email.

    Returns:
        Tuple of (subject, html_body).
    """
    subject = "Вы записаны на курс: {course_title}".format(course_title=course_title)
    content = (
        '<h1 style="margin:0 0 16px 0;font-size:22px;color:#111827;">'
        'Привет, {user_name}!</h1>'
        '<p style="margin:0 0 16px 0;font-size:16px;color:#374151;line-height:1.5;">'
        'Вы успешно записаны на курс '
        '<strong>{course_title}</strong>.</p>'
        '<p style="margin:0 0 24px 0;font-size:16px;color:#374151;line-height:1.5;">'
        'Начните обучение прямо сейчас!</p>'
        '<div style="text-align:center;margin:24px 0;">'
        '<a href="{course_url}" style="display:inline-block;padding:14px 32px;'
        'background-color:#2563eb;color:#ffffff;text-decoration:none;'
        'border-radius:6px;font-size:16px;font-weight:bold;">'
        'Перейти к курсу</a></div>'
    ).format(user_name=user_name, course_title=course_title, course_url=course_url)
    return subject, base_template(content)
