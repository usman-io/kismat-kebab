from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from core.services.mailersend import MailerSendError, MailerSendService

from .models import EmailVerificationToken, User


def build_verification_url(token):
    path = reverse('accounts:verify_email', kwargs={'token': token})
    return f'{settings.SITE_URL.rstrip("/")}{path}'


def create_verification_token(user):
    """Create a new verification token and invalidate previous unused ones."""
    EmailVerificationToken.objects.filter(
        user=user,
        used_at__isnull=True,
    ).update(used_at=timezone.now())

    expires_at = timezone.now() + timedelta(
        hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS,
    )
    return EmailVerificationToken.objects.create(
        user=user,
        expires_at=expires_at,
    )


def send_verification_email(user):
    """
    Create token and send verification email via MailerSend.

    Returns (success: bool, error_message: str | None).
    """
    token_obj = create_verification_token(user)
    verification_url = build_verification_url(token_obj.token)

    try:
        sent = MailerSendService.send_verification_email(user, verification_url)
        if sent:
            return True, None
        return False, (
            'Email service is not configured. Please contact support or try again later.'
        )
    except MailerSendError as exc:
        return False, str(exc)


def verify_email_token(token_uuid):
    """
    Validate and consume a verification token.

    Returns (user, error_message). user is None on failure.
    """
    try:
        token_obj = EmailVerificationToken.objects.select_related('user').get(
            token=token_uuid,
        )
    except EmailVerificationToken.DoesNotExist:
        return None, 'This verification link is invalid.'

    if not token_obj.is_valid:
        if token_obj.used_at:
            return None, 'This verification link has already been used.'
        return None, 'This verification link has expired. Please request a new one.'

    user = token_obj.user
    token_obj.mark_used()
    user.mark_email_verified()
    return user, None
