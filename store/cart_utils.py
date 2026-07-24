"""Cart management utilities — add, update, remove items, apply coupons."""

from decimal import Decimal

from django.db import transaction

from .models import Cart, CartItem, Coupon, ExtraOption, MenuItem


def get_or_create_cart(request):
    """Get or create a cart for the current request (session-based or user-linked)."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        session_key = request.session.session_key
        if session_key:
            session_cart = Cart.objects.filter(session_key=session_key).exclude(
                user=request.user,
            ).first()
            if session_cart:
                _merge_carts(session_cart, cart)
                session_cart.delete()
        return cart
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
        return cart


def _merge_carts(source_cart, target_cart):
    """Merge items from source_cart into target_cart."""
    for source_item in source_cart.items.all():
        cart_item, created = CartItem.objects.get_or_create(
            cart=target_cart,
            menu_item=source_item.menu_item,
            defaults={
                'quantity': source_item.quantity,
                'extras_data': source_item.extras_data,
                'special_instructions': source_item.special_instructions,
            },
        )
        if not created:
            cart_item.quantity += source_item.quantity
            if source_item.extras_data:
                cart_item.extras_data = source_item.extras_data
            cart_item.save()


def add_to_cart(request, menu_item_id, quantity=1, extras_ids=None, instructions=''):
    """
    Add a menu item to the cart.

    Returns (success: bool, message: str, cart_item: CartItem | None).
    """
    try:
        menu_item = MenuItem.objects.get(id=menu_item_id, is_available=True)
    except MenuItem.DoesNotExist:
        return False, 'Menu item not found.', None

    cart = get_or_create_cart(request)
    extras_ids = extras_ids or []

    # Validate extras exist and belong to this item's groups
    if extras_ids:
        valid_extra_ids = set(
            ExtraOption.objects.filter(
                id__in=extras_ids,
                is_available=True,
                group__menu_items__menu_item=menu_item,
            ).values_list('id', flat=True)
        )
        extras_ids = list(valid_extra_ids)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        menu_item=menu_item,
        defaults={
            'quantity': quantity,
            'extras_data': extras_ids,
            'special_instructions': instructions,
        },
    )

    if not created:
        cart_item.quantity += quantity
        if extras_ids:
            # Merge new extras, avoiding duplicates
            existing = set(cart_item.extras_data or [])
            existing.update(extras_ids)
            cart_item.extras_data = list(existing)
        if instructions:
            cart_item.special_instructions = instructions
        cart_item.save()

    return True, f'{menu_item.name} added to cart!', cart_item


def update_cart_item(request, cart_item_id, quantity=None, extras_ids=None, instructions=None):
    """
    Update an existing cart item.

    Returns (success: bool, message: str).
    """
    try:
        cart_item = CartItem.objects.get(
            id=cart_item_id,
            cart=get_or_create_cart(request),
        )
    except CartItem.DoesNotExist:
        return False, 'Item not found in cart.'

    if quantity is not None:
        if quantity <= 0:
            cart_item.delete()
            return True, 'Item removed from cart.'
        cart_item.quantity = quantity

    if extras_ids is not None:
        cart_item.extras_data = extras_ids

    if instructions is not None:
        cart_item.special_instructions = instructions

    cart_item.save()
    return True, 'Cart updated.'


def remove_from_cart(request, cart_item_id):
    """Remove an item from the cart."""
    try:
        cart_item = CartItem.objects.get(
            id=cart_item_id,
            cart=get_or_create_cart(request),
        )
        cart_item.delete()
        return True, 'Item removed from cart.'
    except CartItem.DoesNotExist:
        return False, 'Item not found in cart.'


def clear_cart(request):
    """Remove all items from the cart."""
    cart = get_or_create_cart(request)
    cart.items.all().delete()
    cart.coupon = None
    cart.save()


def get_cart_subtotal(cart):
    """Calculate the subtotal of all items in the cart."""
    return sum(item.total_price for item in cart.items.all())


def apply_coupon_to_cart(request, code):
    """
    Apply a coupon to the cart.

    Returns (success: bool, message: str, discount_amount: Decimal).
    """
    cart = get_or_create_cart(request)

    try:
        coupon = Coupon.objects.get(code__iexact=code.strip(), is_active=True)
    except Coupon.DoesNotExist:
        return False, 'Invalid coupon code.', Decimal('0.00')

    if not coupon.is_valid:
        if coupon.max_uses > 0 and coupon.current_uses >= coupon.max_uses:
            return False, 'This coupon has reached its usage limit.', Decimal('0.00')
        return False, 'This coupon has expired.', Decimal('0.00')

    subtotal = get_cart_subtotal(cart)
    if subtotal < coupon.min_spend:
        return False, (
            f'Minimum spend of £{coupon.min_spend:.2f} required for this coupon. '
            f'Current subtotal: £{subtotal:.2f}'
        ), Decimal('0.00')

    cart.coupon = coupon
    cart.save()

    discount = coupon.calculate_discount(subtotal)
    return True, f'Coupon "{coupon.code}" applied! You save £{discount:.2f}.', discount


def remove_coupon_from_cart(request):
    """Remove the applied coupon from the cart."""
    cart = get_or_create_cart(request)
    cart.coupon = None
    cart.save()
    return True, 'Coupon removed.'


def get_cart_data(request):
    """
    Get full cart data for template rendering.

    Returns dict with items, subtotal, discount, total, item_count.
    """
    cart = get_or_create_cart(request)
    items = cart.items.select_related('menu_item__category').all()

    cart_items = []
    for item in items:
        cart_items.append({
            'id': item.id,
            'menu_item': item.menu_item,
            'quantity': item.quantity,
            'extras_data': item.extras_data,
            'selected_extras': item.selected_extras,
            'extras_total': item.extras_total,
            'unit_price': item.unit_price,
            'total_price': item.total_price,
            'special_instructions': item.special_instructions,
        })

    subtotal = cart.subtotal
    coupon = cart.coupon
    discount = cart.discount_amount
    total = cart.total
    item_count = cart.item_count

    return {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'coupon': coupon,
        'discount': discount,
        'total': total,
        'item_count': item_count,
    }


@transaction.atomic
def create_order_from_cart(request, order_type, delivery_details=None):
    """
    Convert the current cart into an Order.

    Returns (success: bool, message: str, order: Order | None).
    """
    from django.utils import timezone

    from .models import Order, OrderItem

    cart = get_or_create_cart(request)
    items = cart.items.select_related('menu_item').all()

    if not items:
        return False, 'Your cart is empty.', None

    subtotal = cart.subtotal
    coupon = cart.coupon
    discount = cart.discount_amount if coupon else Decimal('0.00')
    delivery_fee = Decimal('0.00')

    if order_type == 'delivery':
        # Free delivery over £15
        delivery_fee = Decimal('0.00') if subtotal >= Decimal('15.00') else Decimal('2.99')

    total = subtotal - discount + delivery_fee

    # Build delivery details
    details = delivery_details or {}

    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key if not request.user.is_authenticated else None,
        order_type=order_type,
        status=Order.Status.PENDING,
        subtotal=subtotal,
        discount_amount=discount,
        delivery_fee=delivery_fee,
        total=total,
        coupon=coupon,
        delivery_name=details.get('name', ''),
        delivery_phone=details.get('phone', ''),
        delivery_address=details.get('address', ''),
        delivery_postcode=details.get('postcode', ''),
        delivery_notes=details.get('notes', ''),
    )

    # Create order items
    for item in items:
        extras_snapshot = []
        for extra in item.selected_extras:
            extras_snapshot.append({
                'name': extra.name,
                'price': str(extra.price),
                'group': extra.group.name,
            })

        OrderItem.objects.create(
            order=order,
            menu_item=item.menu_item,
            menu_item_name=item.menu_item.name,
            menu_item_price=item.menu_item.price,
            quantity=item.quantity,
            extras_data=extras_snapshot,
            extras_total=item.extras_total,
            unit_price=item.unit_price,
            total_price=item.total_price,
        )

    # Increment coupon usage
    if coupon:
        coupon.increment_usage()

    # Clear the cart
    cart.items.all().delete()
    cart.coupon = None
    cart.save()

    return True, f'Order #{order.order_number} placed successfully!', order

