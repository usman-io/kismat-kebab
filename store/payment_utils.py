"""Stripe payment integration utilities."""

from decimal import Decimal

import stripe
from django.conf import settings
from django.db import transaction

from .models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment_intent(order: Order) -> tuple:
    """
    Create a Stripe PaymentIntent for the given order.

    Returns (success: bool, client_secret: str | None, error: str | None).
    """
    if not settings.STRIPE_SECRET_KEY:
        return False, None, 'Stripe is not configured. Please set STRIPE_SECRET_KEY.'

    try:
        # Convert Decimal to integer cents (or pence)
        amount_cents = int(order.total * Decimal('100'))

        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='gbp',
            metadata={
                'order_number': order.order_number,
                'order_id': str(order.id),
            },
            description=f'Order #{order.order_number} — {settings.SITE_NAME}',
        )

        # Store the PaymentIntent ID on the order
        order.stripe_payment_intent_id = intent.id
        order.save(update_fields=['stripe_payment_intent_id'])

        return True, intent.client_secret, None

    except stripe.error.StripeError as e:
        return False, None, str(e)


def handle_payment_success(payment_intent_id: str) -> tuple:
    """
    Handle a successful Stripe payment.
    Marks the order as paid and confirmed.

    Returns (success: bool, order: Order | None, error: str | None).
    """
    from django.utils import timezone

    try:
        order = Order.objects.get(stripe_payment_intent_id=payment_intent_id)
    except Order.DoesNotExist:
        return False, None, f'No order found for PaymentIntent {payment_intent_id}'

    if order.is_paid:
        # Already processed — idempotent
        return True, order, None

    with transaction.atomic():
        order.is_paid = True
        # Only auto-confirm if status is still pending
        if order.status == Order.Status.PENDING:
            order.status = Order.Status.CONFIRMED
            order.confirmed_at = timezone.now()
        order.save(update_fields=['is_paid', 'status', 'confirmed_at'])

    return True, order, None


def handle_payment_failed(payment_intent_id: str) -> tuple:
    """
    Handle a failed Stripe payment.

    Returns (success: bool, order: Order | None, error: str | None).
    """
    try:
        order = Order.objects.get(stripe_payment_intent_id=payment_intent_id)
    except Order.DoesNotExist:
        return False, None, f'No order found for PaymentIntent {payment_intent_id}'

    return True, order, 'Payment failed.'

