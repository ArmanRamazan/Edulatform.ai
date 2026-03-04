"""Review received email template."""

from __future__ import annotations

from app.templates.base import base_template


def review_email(
    teacher_name: str, course_title: str, rating: int, review_text: str
) -> tuple[str, str]:
    """Generate new review notification email for teachers.

    Returns:
        Tuple of (subject, html_body).
    """
    subject = "Новый отзыв на курс: {course_title}".format(course_title=course_title)
    stars = "★" * rating + "☆" * (5 - rating)
    content = (
        '<h1 style="margin:0 0 16px 0;font-size:22px;color:#111827;">'
        'Здравствуйте, {teacher_name}!</h1>'
        '<p style="margin:0 0 16px 0;font-size:16px;color:#374151;line-height:1.5;">'
        'На ваш курс <strong>{course_title}</strong> оставлен новый отзыв.</p>'
        '<div style="margin:0 0 16px 0;padding:16px;background-color:#f9fafb;'
        'border-radius:6px;border:1px solid #e5e7eb;">'
        '<p style="margin:0 0 8px 0;font-size:20px;color:#f59e0b;">{stars}</p>'
        '<p style="margin:0;font-size:16px;color:#374151;font-style:italic;">'
        '&ldquo;{review_text}&rdquo;</p>'
        '</div>'
    ).format(
        teacher_name=teacher_name,
        course_title=course_title,
        stars=stars,
        review_text=review_text,
    )
    return subject, base_template(content)
