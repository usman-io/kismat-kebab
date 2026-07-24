import json
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from .cart_utils import (
    add_to_cart,
    apply_coupon_to_cart,
    clear_cart,
    create_order_from_cart,
    get_cart_data,
    remove_coupon_from_cart,
    remove_from_cart,
    update_cart_item,
)
from .menu_utils import get_active_categories, get_filter_state, get_menu_items
from .models import (
    Cart, CartItem, Category, FavouriteItem, MenuItem, Order, Review,
)
from .payment_utils import create_payment_intent, handle_payment_success, handle_payment_failed


def home(request):
    categories = get_active_categories()[:6]

    # Annotate featured items with review stats
    rating_subq = Review.objects.filter(
        menu_item=OuterRef('pk'),
        is_approved=True,
    ).values('menu_item').annotate(
        avg=Avg('rating'),
        cnt=Count('id'),
    ).values('avg', 'cnt')

    featured_items = MenuItem.objects.filter(
        is_available=True,
        is_featured=True,
    ).select_related('category').annotate(
        avg_rating=Subquery(rating_subq.values('avg')),
        review_count=Subquery(rating_subq.values('cnt')),
    )[:8]

    cart_data = get_cart_data(request)
    return render(request, 'store/home.html', {
        'categories': categories,
        'featured_items': featured_items,
        'cart_data': cart_data,
    })


def menu_list(request):
    categories = get_active_categories()
    items = get_menu_items(request.GET)
    filters = get_filter_state(request.GET)
    cart_data = get_cart_data(request)
    return render(request, 'store/menu_list.html', {
        'categories': categories,
        'items': items,
        'filters': filters,
        'result_count': items.count(),
        'cart_data': cart_data,
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    items = get_menu_items(request.GET, category=category)
    filters = get_filter_state(request.GET)
    categories = get_active_categories()
    cart_data = get_cart_data(request)
    return render(request, 'store/category_detail.html', {
        'category': category,
        'categories': categories,
        'items': items,
        'filters': filters,
        'result_count': items.count(),
        'cart_data': cart_data,
    })


def menu_item_detail(request, slug):
    item = get_object_or_404(
        MenuItem.objects.select_related('category').prefetch_related(
            'extra_groups__extra_group__options',
            'reviews__user',
        ),
        slug=slug,
        is_available=True,
    )
    extra_groups = [
        link.extra_group for link in item.extra_groups.all()
        if link.extra_group.options.filter(is_available=True).exists()
    ]
    related_items = MenuItem.objects.filter(
        category=item.category,
        is_available=True,
    ).exclude(pk=item.pk)[:4]

    # Reviews
    reviews = item.reviews.filter(is_approved=True).select_related('user')[:10]
    avg_rating = item.reviews.filter(is_approved=True).aggregate(
        avg=Avg('rating'), count=Count('id'),
    )

    # Check if user has favourited this item
    user_favourite = False
    if request.user.is_authenticated:
        user_favourite = FavouriteItem.objects.filter(
            user=request.user, menu_item=item,
        ).exists()

    cart_data = get_cart_data(request)

    return render(request, 'store/menu_item_detail.html', {
        'item': item,
        'extra_groups': extra_groups,
        'related_items': related_items,
        'reviews': reviews,
        'avg_rating': avg_rating['avg'],
        'review_count': avg_rating['count'],
        'user_favourite': user_favourite,
        'cart_data': cart_data,
    })


# ──────── Cart Views ────────


def cart_detail(request):
    """Display the shopping cart page."""
    cart_data = get_cart_data(request)
    return render(request, 'store/cart.html', {
        'cart_data': cart_data,
    })


@require_POST
def add_to_cart_view(request):
    """Add an item to cart via POST."""
    menu_item_id = request.POST.get('menu_item_id')
    quantity = int(request.POST.get('quantity', 1))
    extras = request.POST.getlist('extras')
    extras_ids = [int(e) for e in extras if e.isdigit()]
    instructions = request.POST.get('instructions', '')

    success, message, cart_item = add_to_cart(
        request, menu_item_id, quantity, extras_ids, instructions,
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_data = get_cart_data(request)
        return JsonResponse({
            'success': success,
            'message': message,
            'item_count': cart_data['item_count'],
            'total': str(cart_data['total']),
        })

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    # Redirect back to the menu item page or menu
    redirect_to = request.POST.get('next', 'store:menu')
    return redirect(redirect_to)


@require_POST
def update_cart_view(request):
    """Update a cart item (quantity, extras)."""
    cart_item_id = request.POST.get('cart_item_id')
    quantity = request.POST.get('quantity')

    if quantity is not None:
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = None

    success, message = update_cart_item(request, cart_item_id, quantity=quantity)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_data = get_cart_data(request)
        return JsonResponse({
            'success': success,
            'message': message,
            'item_count': cart_data['item_count'],
            'subtotal': str(cart_data['subtotal']),
            'discount': str(cart_data['discount']),
            'total': str(cart_data['total']),
        })

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('store:cart')


@require_POST
def remove_from_cart_view(request):
    """Remove an item from cart."""
    cart_item_id = request.POST.get('cart_item_id')
    success, message = remove_from_cart(request, cart_item_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_data = get_cart_data(request) if CartItem.objects.filter(
            cart=get_cart_data(request)['cart'], id=cart_item_id,
        ).exists() else get_cart_data(request)
        return JsonResponse({
            'success': success,
            'message': message,
            'item_count': cart_data['item_count'],
            'subtotal': str(cart_data['subtotal']),
            'total': str(cart_data['total']),
        })

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('store:cart')


# ──────── Coupon Views ────────


@require_POST
def apply_coupon_view(request):
    """Apply a coupon code to the cart."""
    code = request.POST.get('code', '')
    success, message, discount = apply_coupon_to_cart(request, code)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_data = get_cart_data(request)
        return JsonResponse({
            'success': success,
            'message': message,
            'discount': str(cart_data['discount']),
            'total': str(cart_data['total']),
            'coupon_code': cart_data['coupon'].code if cart_data['coupon'] else None,
        })

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect('store:cart')


@require_POST
def remove_coupon_view(request):
    """Remove the applied coupon from cart."""
    success, message = remove_coupon_from_cart(request)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_data = get_cart_data(request)
        return JsonResponse({
            'success': success,
            'message': message,
            'discount': str(cart_data['discount']),
            'total': str(cart_data['total']),
        })

    messages.success(request, message)
    return redirect('store:cart')


# ──────── Checkout Views ────────


@require_http_methods(['GET', 'POST'])
def checkout(request):
    """Checkout page with Stripe payment integration."""
    cart_data = get_cart_data(request)

    if cart_data['item_count'] == 0:
        messages.warning(request, 'Your cart is empty.')
        return redirect('store:menu')

    if request.method == 'POST':
        order_type = request.POST.get('order_type', 'delivery')
        delivery_details = {
            'name': request.POST.get('name', ''),
            'phone': request.POST.get('phone', ''),
            'address': request.POST.get('address', ''),
            'postcode': request.POST.get('postcode', ''),
            'notes': request.POST.get('notes', ''),
        }

        # Validate delivery details
        if order_type == 'delivery':
            if not delivery_details['name'] or not delivery_details['address']:
                messages.error(request, 'Please provide your name and delivery address.')
                return render(request, 'store/checkout.html', {
                    'cart_data': cart_data,
                    'order_type': order_type,
                    'delivery_details': delivery_details,
                    'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
                })

        # Create the order (status = pending, not confirmed until payment)
        success, message, order = create_order_from_cart(
            request, order_type, delivery_details,
        )

        if not success:
            messages.error(request, message)
            return redirect('store:cart')

        # Create Stripe PaymentIntent for the order
        pi_success, client_secret, pi_error = create_payment_intent(order)

        if not pi_success:
            messages.error(
                request,
                f'Payment could not be initialised: {pi_error}. Please try again.',
            )
            return redirect('store:cart')

        return render(request, 'store/checkout.html', {
            'cart_data': cart_data,
            'order_type': order_type,
            'delivery_details': delivery_details,
            'order': order,
            'client_secret': client_secret,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
            'needs_payment': True,
        })

    # GET request — pre-fill user details
    delivery_details = {
        'name': '',
        'phone': '',
        'address': '',
        'postcode': '',
        'notes': '',
    }
    if request.user.is_authenticated:
        delivery_details['name'] = request.user.full_name
        delivery_details['phone'] = request.user.phone

    return render(request, 'store/checkout.html', {
        'cart_data': cart_data,
        'order_type': 'delivery',
        'delivery_details': delivery_details,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


def order_confirmation(request, order_number):
    """Order placed successfully confirmation page."""
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, 'store/order_confirmation.html', {
        'order': order,
    })


# ──────── Stripe Webhook ────────


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe webhook endpoint for async payment confirmations.
    Handles `payment_intent.succeeded` and `payment_intent.payment_failed`.
    """
    import stripe

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    # Verify webhook signature if secret is configured
    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET,
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        # Fallback: parse event directly (not recommended for production)
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid payload'}, status=400)

    event_type = event.get('type', '')

    if event_type == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        intent_id = payment_intent['id']
        success, order, error = handle_payment_success(intent_id)
        if not success:
            return JsonResponse({'error': error}, status=404)

    elif event_type == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        intent_id = payment_intent['id']
        success, order, error = handle_payment_failed(intent_id)
        if not success:
            return JsonResponse({'error': error}, status=404)

    return JsonResponse({'status': 'ok'})


# ──────── Order Views ────────


def order_detail(request, order_number):
    """View a specific order."""
    if request.user.is_authenticated:
        order = get_object_or_404(
            Order.objects.prefetch_related('items'),
            order_number=order_number,
            user=request.user,
        )
    else:
        session_key = request.session.session_key
        order = get_object_or_404(
            Order.objects.prefetch_related('items'),
            order_number=order_number,
            session_key=session_key,
        )

    can_review = order.status in [
        Order.Status.DELIVERED, Order.Status.COLLECTED,
    ]

    return render(request, 'store/order_detail.html', {
        'order': order,
        'can_review': can_review,
    })


def order_tracking(request, order_number):
    """Live order status tracking page."""
    if request.user.is_authenticated:
        order = get_object_or_404(
            Order.objects.prefetch_related('items'),
            order_number=order_number,
            user=request.user,
        )
    else:
        session_key = request.session.session_key
        order = get_object_or_404(
            Order.objects.prefetch_related('items'),
            order_number=order_number,
            session_key=session_key,
        )

    return render(request, 'store/order_tracking.html', {
        'order': order,
    })


def order_history(request):
    """View past orders."""
    if not request.user.is_authenticated:
        messages.info(request, 'Please sign in to view your order history.')
        return redirect('accounts:login')

    orders = Order.objects.filter(user=request.user).prefetch_related('items')[:20]
    return render(request, 'store/order_history.html', {
        'orders': orders,
    })


@require_POST
def cancel_order(request, order_number):
    """Cancel an order if it's still cancellable."""
    if request.user.is_authenticated:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
    else:
        session_key = request.session.session_key
        order = get_object_or_404(Order, order_number=order_number, session_key=session_key)

    if not order.is_cancellable:
        messages.error(request, 'This order can no longer be cancelled.')
        return redirect('store:order_detail', order_number=order_number)

    from django.utils import timezone
    order.status = Order.Status.CANCELLED
    order.cancelled_at = timezone.now()
    order.save(update_fields=['status', 'cancelled_at'])

    messages.success(request, f'Order #{order.order_number} has been cancelled.')
    return redirect('store:order_detail', order_number=order_number)


@require_POST
def repeat_order(request, order_number):
    """Repeat a previous order — add all items from that order to cart."""
    if request.user.is_authenticated:
        order = get_object_or_404(
            Order.objects.prefetch_related('items'),
            order_number=order_number,
            user=request.user,
        )
    else:
        session_key = request.session.session_key
        order = get_object_or_404(
            Order.objects.prefetch_related('items'),
            order_number=order_number,
            session_key=session_key,
        )

    for order_item in order.items.all():
        if order_item.menu_item and order_item.menu_item.is_available:
            # Try to map extras back
            extras_ids = []
            for extra in order_item.extras_data:
                try:
                    extra_obj = order_item.menu_item.extra_groups.filter(
                        extra_group__options__name=extra.get('name', ''),
                    ).first()
                    if extra_obj:
                        opt = extra_obj.extra_group.options.filter(
                            name=extra.get('name', ''),
                        ).first()
                        if opt:
                            extras_ids.append(opt.id)
                except Exception:
                    pass

            add_to_cart(
                request,
                order_item.menu_item.id,
                quantity=order_item.quantity,
                extras_ids=extras_ids,
            )

    messages.success(
        request,
        f'All items from Order #{order_number} have been added to your cart.',
    )
    return redirect('store:cart')


# ──────── Review Views ────────


@require_POST
@login_required
def add_review(request):
    """
    Legacy review endpoint — now redirects to order-based review.
    Reviews can only be submitted via an order.
    """
    messages.error(
        request,
        'Reviews can only be submitted through your order history. '
        'Please go to your order and leave a review there.',
    )
    return redirect('store:order_history')


@require_POST
@login_required
def add_order_review(request, order_number):
    """
    Submit a single rating & comment for an entire order.
    The same rating is applied to EVERY item in the order.
    Only one review per (user, order, menu_item) combination is allowed.
    """
    order = get_object_or_404(
        Order.objects.prefetch_related('items__menu_item'),
        order_number=order_number,
        user=request.user,
    )

    # Ensure order is deliverable for reviews
    if order.status not in [Order.Status.DELIVERED, Order.Status.COLLECTED]:
        messages.error(request, 'You can only review completed orders.')
        return redirect('store:order_detail', order_number=order_number)

    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '')

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, 'Please provide a valid rating (1-5).')
        return redirect('store:order_detail', order_number=order_number)

    # Check if this order has already been reviewed entirely
    existing_reviews = Review.objects.filter(
        user=request.user,
        order=order,
    )
    if existing_reviews.exists():
        # Update all reviews for this order with the new rating/comment
        existing_reviews.update(rating=rating, comment=comment)
        messages.success(request, 'Your review has been updated for all items in this order!')
        return redirect('store:order_detail', order_number=order_number)

    # Create a review for EACH menu item in the order with the same rating
    reviewed_count = 0
    for order_item in order.items.all():
        if order_item.menu_item:
            review, created = Review.objects.get_or_create(
                menu_item=order_item.menu_item,
                user=request.user,
                order=order,
                defaults={
                    'rating': rating,
                    'comment': comment,
                },
            )
            if created:
                reviewed_count += 1
            else:
                # Update existing individual review
                review.rating = rating
                review.comment = comment
                review.save()

    if reviewed_count > 0:
        messages.success(
            request,
            f'Your {rating}-star rating has been applied to all {reviewed_count} item(s) in this order!',
        )
    else:
        messages.info(request, 'Your review rating has been updated.')

    return redirect('store:order_detail', order_number=order_number)


# ──────── Favourite Views ────────


@require_POST
@login_required
def toggle_favourite(request):
    """Toggle a menu item as favourite."""
    menu_item_id = request.POST.get('menu_item_id')

    try:
        menu_item = MenuItem.objects.get(id=menu_item_id, is_available=True)
    except MenuItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Menu item not found.'})

    favourite, created = FavouriteItem.objects.get_or_create(
        user=request.user,
        menu_item=menu_item,
    )

    if not created:
        favourite.delete()
        is_favourite = False
        message = f'{menu_item.name} removed from favourites.'
    else:
        is_favourite = True
        message = f'{menu_item.name} added to favourites!'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_favourite': is_favourite,
            'message': message,
        })

    messages.success(request, message)
    return redirect('store:menu_item', slug=menu_item.slug)


@login_required
def favourite_list(request):
    """View user's favourite items."""
    favourites = FavouriteItem.objects.filter(
        user=request.user,
        menu_item__is_available=True,
    ).select_related('menu_item__category')[:50]

    cart_data = get_cart_data(request)

    return render(request, 'store/favourites.html', {
        'favourites': favourites,
        'cart_data': cart_data,
    })

