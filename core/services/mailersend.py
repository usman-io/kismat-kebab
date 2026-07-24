"""
MailerSend email integration.
API docs: https://developers.mailersend.com/
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

MAILERSEND_API_URL = 'https://api.mailersend.com/v1/email'


class MailerSendError(Exception):
    """Raised when MailerSend API returns an error."""


class MailerSendService:
    """Send transactional emails via MailerSend REST API."""

    @staticmethod
    def _headers():
        return {
            'Authorization': f'Bearer {settings.MAILERSEND_API_TOKEN}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    @classmethod
    def send_email(cls, to_email, to_name, subject, html_content, text_content=None):
        """
        Send a single email via MailerSend.

        Returns True on success, raises MailerSendError on failure.
        """
        if not settings.MAILERSEND_API_TOKEN:
            logger.warning('MAILERSEND_API_TOKEN not set — email not sent to %s', to_email)
            return False

        payload = {
            'from': {
                'email': settings.MAILERSEND_FROM_EMAIL,
                'name': settings.MAILERSEND_FROM_NAME,
            },
            'to': [{'email': to_email, 'name': to_name or to_email}],
            'subject': subject,
            'html': html_content,
        }
        if text_content:
            payload['text'] = text_content

        try:
            response = requests.post(
                MAILERSEND_API_URL,
                json=payload,
                headers=cls._headers(),
                timeout=30,
            )
            if response.status_code in (200, 202):
                return True
            logger.error(
                'MailerSend error %s: %s',
                response.status_code,
                response.text,
            )
            raise MailerSendError(f'MailerSend returned {response.status_code}')
        except requests.RequestException as exc:
            logger.exception('MailerSend request failed')
            raise MailerSendError(str(exc)) from exc

    @classmethod
    def send_verification_email(cls, user, verification_url):
        """Send email verification link to a newly registered customer."""
        subject = f'Verify your email — {settings.SITE_NAME}'
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #e63946;">Welcome to {settings.SITE_NAME}!</h2>
            <p>Hi {user.first_name or 'there'},</p>
            <p>Thanks for signing up. Please verify your email address to start ordering
            delicious fast food in {settings.SITE_CITY}.</p>
            <p style="margin: 32px 0;">
                <a href="{verification_url}"
                   style="background: #e63946; color: #fff; padding: 14px 28px;
                          text-decoration: none; border-radius: 8px; font-weight: bold;">
                    Verify Email Address
                </a>
            </p>
            <p style="color: #666; font-size: 14px;">
                Or copy this link: {verification_url}
            </p>
            <p style="color: #666; font-size: 14px;">
                This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS} hours.
            </p>
        </div>
        """
        text_content = (
            f'Welcome to {settings.SITE_NAME}!\n\n'
            f'Please verify your email: {verification_url}\n\n'
            f'This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS} hours.'
        )
        return cls.send_email(
            to_email=user.email,
            to_name=user.full_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )
