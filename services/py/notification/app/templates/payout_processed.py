"""Payout processed email template."""

from __future__ import annotations

from app.templates.base import base_template


def payout_email(
    teacher_name: str, amount: float, currency: str = "RUB"
) -> tuple[str, str]:
    """Generate payout processed notification email for teachers.

    Returns:
        Tuple of (subject, html_body).
    """
    subject = "Выплата обработана"
    formatted_amount = "{amount:.2f} {currency}".format(
        amount=amount, currency=currency
    )
    content = (
        '<h1 style="margin:0 0 16px 0;font-size:22px;color:#111827;">'
        'Здравствуйте, {teacher_name}!</h1>'
        '<p style="margin:0 0 16px 0;font-size:16px;color:#374151;line-height:1.5;">'
        'Ваша выплата успешно обработана.</p>'
        '<div style="margin:0 0 16px 0;padding:16px;background-color:#f0fdf4;'
        'border-radius:6px;border:1px solid #bbf7d0;">'
        '<p style="margin:0;font-size:24px;color:#16a34a;font-weight:bold;'
        'text-align:center;">{formatted_amount}</p>'
        '</div>'
        '<p style="margin:0 0 0 0;font-size:14px;color:#6b7280;line-height:1.5;">'
        'Средства поступят на ваш счёт в течение 3–5 рабочих дней.</p>'
    ).format(teacher_name=teacher_name, formatted_amount=formatted_amount)
    return subject, base_template(content)
