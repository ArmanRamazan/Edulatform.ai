"""Tests for HTML email templates."""

import pytest

from app.templates.base import base_template
from app.templates.welcome import welcome_email
from app.templates.email_verification import verification_email
from app.templates.password_reset import password_reset_email
from app.templates.enrollment_confirmation import enrollment_email
from app.templates.course_completion import completion_email
from app.templates.review_received import review_email
from app.templates.payout_processed import payout_email
from app.templates import get_email_template


class TestBaseTemplate:
    def test_returns_html_string(self):
        result = base_template("<p>Hello</p>")
        assert isinstance(result, str)

    def test_contains_doctype(self):
        result = base_template("<p>Hello</p>")
        assert "<!DOCTYPE html>" in result

    def test_contains_utf8_charset(self):
        result = base_template("<p>Hello</p>")
        assert 'charset="UTF-8"' in result or "charset=UTF-8" in result

    def test_contains_content(self):
        result = base_template("<p>Test content here</p>")
        assert "Test content here" in result

    def test_contains_header_logo(self):
        result = base_template("<p>Hello</p>")
        assert "EduPlatform" in result

    def test_contains_footer(self):
        result = base_template("<p>Hello</p>")
        assert "зарегистрированы на EduPlatform" in result

    def test_contains_unsubscribe_link(self):
        result = base_template("<p>Hello</p>")
        assert "Отписаться от рассылки" in result

    def test_custom_unsubscribe_url(self):
        result = base_template("<p>Hello</p>", unsubscribe_url="https://example.com/unsub")
        assert "https://example.com/unsub" in result

    def test_default_unsubscribe_url_is_hash(self):
        result = base_template("<p>Hello</p>")
        assert 'href="#"' in result

    def test_max_width_600(self):
        result = base_template("<p>Hello</p>")
        assert "600px" in result


class TestWelcomeEmail:
    def test_returns_tuple(self):
        subject, html = welcome_email("Иван")
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject(self):
        subject, _ = welcome_email("Иван")
        assert subject == "Добро пожаловать в EduPlatform!"

    def test_contains_user_name(self):
        _, html = welcome_email("Иван")
        assert "Иван" in html

    def test_contains_cta_button(self):
        _, html = welcome_email("Иван")
        assert "Начать обучение" in html

    def test_wrapped_in_base_template(self):
        _, html = welcome_email("Иван")
        assert "<!DOCTYPE html>" in html
        assert "Отписаться от рассылки" in html


class TestVerificationEmail:
    def test_returns_tuple(self):
        subject, html = verification_email("Иван", "https://example.com/verify")
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject(self):
        subject, _ = verification_email("Иван", "https://example.com/verify")
        assert subject == "Подтвердите email"

    def test_contains_user_name(self):
        _, html = verification_email("Иван", "https://example.com/verify")
        assert "Иван" in html

    def test_contains_verify_url(self):
        _, html = verification_email("Иван", "https://example.com/verify?token=abc")
        assert "https://example.com/verify?token=abc" in html

    def test_contains_cta_button(self):
        _, html = verification_email("Иван", "https://example.com/verify")
        assert "Подтвердить email" in html

    def test_contains_expiry_note(self):
        _, html = verification_email("Иван", "https://example.com/verify")
        assert "срок" in html.lower() or "час" in html.lower() or "действ" in html.lower()


class TestPasswordResetEmail:
    def test_returns_tuple(self):
        subject, html = password_reset_email("Иван", "https://example.com/reset")
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject(self):
        subject, _ = password_reset_email("Иван", "https://example.com/reset")
        assert subject == "Сброс пароля"

    def test_contains_user_name(self):
        _, html = password_reset_email("Иван", "https://example.com/reset")
        assert "Иван" in html

    def test_contains_reset_url(self):
        _, html = password_reset_email("Иван", "https://example.com/reset?token=xyz")
        assert "https://example.com/reset?token=xyz" in html

    def test_contains_cta_button(self):
        _, html = password_reset_email("Иван", "https://example.com/reset")
        assert "Сбросить пароль" in html

    def test_contains_not_requested_note(self):
        _, html = password_reset_email("Иван", "https://example.com/reset")
        assert "не запрашивали" in html.lower() or "игнорируйте" in html.lower()


class TestEnrollmentEmail:
    def test_returns_tuple(self):
        subject, html = enrollment_email("Иван", "Python 101", "https://example.com/course/1")
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject_contains_course_title(self):
        subject, _ = enrollment_email("Иван", "Python 101", "https://example.com/course/1")
        assert "Python 101" in subject

    def test_contains_user_name(self):
        _, html = enrollment_email("Иван", "Python 101", "https://example.com/course/1")
        assert "Иван" in html

    def test_contains_course_title(self):
        _, html = enrollment_email("Иван", "Python 101", "https://example.com/course/1")
        assert "Python 101" in html

    def test_contains_course_url(self):
        _, html = enrollment_email("Иван", "Python 101", "https://example.com/course/1")
        assert "https://example.com/course/1" in html

    def test_contains_cta_button(self):
        _, html = enrollment_email("Иван", "Python 101", "https://example.com/course/1")
        assert "Перейти к курсу" in html


class TestCompletionEmail:
    def test_returns_tuple(self):
        subject, html = completion_email("Иван", "Python 101")
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject(self):
        subject, _ = completion_email("Иван", "Python 101")
        assert "Поздравляем" in subject

    def test_contains_user_name(self):
        _, html = completion_email("Иван", "Python 101")
        assert "Иван" in html

    def test_contains_course_title(self):
        _, html = completion_email("Иван", "Python 101")
        assert "Python 101" in html


class TestReviewEmail:
    def test_returns_tuple(self):
        subject, html = review_email("Иван", "Python 101", 5, "Отличный курс!")
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject_contains_course_title(self):
        subject, _ = review_email("Иван", "Python 101", 5, "Отличный курс!")
        assert "Python 101" in subject

    def test_contains_teacher_name(self):
        _, html = review_email("Иван", "Python 101", 5, "Отличный курс!")
        assert "Иван" in html

    def test_contains_rating_stars(self):
        _, html = review_email("Иван", "Python 101", 4, "Хороший курс")
        # 4 stars = 4 filled stars
        assert html.count("★") == 4

    def test_contains_review_text(self):
        _, html = review_email("Иван", "Python 101", 5, "Отличный курс!")
        assert "Отличный курс!" in html


class TestPayoutEmail:
    def test_returns_tuple(self):
        subject, html = payout_email("Иван", 5000.0)
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject(self):
        subject, _ = payout_email("Иван", 5000.0)
        assert subject == "Выплата обработана"

    def test_contains_teacher_name(self):
        _, html = payout_email("Иван", 5000.0)
        assert "Иван" in html

    def test_contains_amount(self):
        _, html = payout_email("Иван", 5000.0)
        assert "5000" in html or "5 000" in html

    def test_default_currency_rub(self):
        _, html = payout_email("Иван", 5000.0)
        assert "RUB" in html or "₽" in html or "руб" in html.lower()

    def test_custom_currency(self):
        _, html = payout_email("Иван", 100.0, currency="USD")
        assert "USD" in html


class TestGetEmailTemplate:
    def test_welcome(self):
        result = get_email_template("welcome", user_name="Иван")
        assert result is not None
        subject, html = result
        assert subject == "Добро пожаловать в EduPlatform!"

    def test_email_verification(self):
        result = get_email_template(
            "email_verification", user_name="Иван", verify_url="https://example.com/verify"
        )
        assert result is not None

    def test_password_reset(self):
        result = get_email_template(
            "password_reset", user_name="Иван", reset_url="https://example.com/reset"
        )
        assert result is not None

    def test_enrollment_confirmation(self):
        result = get_email_template(
            "enrollment_confirmation",
            user_name="Иван",
            course_title="Python 101",
            course_url="https://example.com/course/1",
        )
        assert result is not None

    def test_course_completion(self):
        result = get_email_template(
            "course_completion", user_name="Иван", course_title="Python 101"
        )
        assert result is not None

    def test_review_received(self):
        result = get_email_template(
            "review_received",
            teacher_name="Иван",
            course_title="Python 101",
            rating=5,
            review_text="Отлично!",
        )
        assert result is not None

    def test_payout_processed(self):
        result = get_email_template(
            "payout_processed", teacher_name="Иван", amount=5000.0
        )
        assert result is not None

    def test_unknown_type_returns_none(self):
        result = get_email_template("unknown_type")
        assert result is None
