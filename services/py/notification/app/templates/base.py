"""Base HTML email template with header, footer, and unsubscribe link."""

from __future__ import annotations


def base_template(content: str, unsubscribe_url: str = "#") -> str:
    """Wrap content in a full HTML email layout.

    Args:
        content: Inner HTML content for the email body.
        unsubscribe_url: URL for the unsubscribe link.

    Returns:
        Complete HTML email string.
    """
    return (
        '<!DOCTYPE html>'
        '<html lang="ru">'
        '<head><meta charset="UTF-8"><meta name="viewport" '
        'content="width=device-width, initial-scale=1.0"></head>'
        '<body style="margin:0;padding:0;background-color:#f4f4f7;'
        'font-family:Arial,Helvetica,sans-serif;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="background-color:#f4f4f7;">'
        '<tr><td align="center" style="padding:24px 0;">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'style="max-width:600px;width:100%;background-color:#ffffff;'
        'border-radius:8px;overflow:hidden;">'
        # Header
        '<tr><td align="center" style="background-color:#2563eb;padding:24px;">'
        '<span style="color:#ffffff;font-size:24px;font-weight:bold;'
        'text-decoration:none;">EduPlatform</span>'
        '</td></tr>'
        # Content
        '<tr><td style="padding:32px 24px;">'
        '{content}'
        '</td></tr>'
        # Footer
        '<tr><td style="padding:16px 24px;background-color:#f9fafb;'
        'border-top:1px solid #e5e7eb;text-align:center;'
        'font-size:12px;color:#6b7280;">'
        '<p style="margin:0 0 8px 0;">'
        'Вы получили это письмо, потому что зарегистрированы на EduPlatform'
        '</p>'
        '<a href="{unsubscribe_url}" style="color:#6b7280;text-decoration:underline;">'
        'Отписаться от рассылки</a>'
        '</td></tr>'
        '</table>'
        '</td></tr></table>'
        '</body></html>'
    ).format(content=content, unsubscribe_url=unsubscribe_url)
