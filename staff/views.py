from decimal import Decimal

from django.contrib import messages
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from store.models import (
    Category, Coupon, MenuItem, Order, OrderItem, Review,
)
from accounts.models import (User)
from store.cart_utils import get_cart_data

from .decorators import staff_required


# ──────── Dashboard ────────


@staff_required
def dashboard(request):
    """Staff dashboard with key metrics and quick overview."""
    today = timezone.now().date()
    today_start = timezone.make_aware(
        timezone.datetime.combine(today, timezone.datetime.min.time())
    )
    today_end = timezone.make_aware(
        timezone.datetime.combine(today, timezone.datetime.max.time())
    )

    # Orders today
    today_orders = Order.objects.filter(created_at__range=[today_start, today_end])
    pending_orders = Order.objects.filter(status=Order.Status.PENDING)

    # Revenue today
    today_revenue = today_orders.aggregate(
        total=Sum('total')
    )['total'] or Decimal('0.00')

    # Order counts by status
    status_counts = {
        label: Order.objects.filter(status=status).count()
        for status, label in Order.Status.choices
    }

    # Recent orders
    recent_orders = Order.objects.select_related('user').prefetch_related('items')[:10]

    # Low stock / unavailable items
    total_menu_items = MenuItem.objects.count()
    available_items = MenuItem.objects.filter(is_available=True).count()
    unavailable_items = total_menu_items - available_items

    # Top selling items (last 30 days)
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    top_items = (
        OrderItem.objects
        .filter(order__created_at__gte=thirty_days_ago)
        .values('menu_item_name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )

    # Recent reviews
    recent_reviews = Review.objects.filter(
        is_approved=False,
    ).select_related('user', 'menu_item')[:5]

    context = {
        'today_orders_count': today_orders.count(),
        'pending_orders_count': pending_orders.count(),
        'today_revenue': today_revenue,
        'status_counts': status_counts,
        'recent_orders': recent_orders,
        'total_menu_items': total_menu_items,
        'available_items': available_items,
        'unavailable_items': unavailable_items,
        'top_items': top_items,
        'recent_reviews': recent_reviews,
        'section': 'dashboard',
    }
    return render(request, 'staff/dashboard.html', context)


# ──────── Orders ────────


@staff_required
def order_list(request):
    """List all orders with filtering by status."""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '').strip()

    orders = Order.objects.select_related('user').prefetch_related('items')

    if status_filter:
        orders = orders.filter(status=status_filter)

    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(delivery_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    orders = orders.order_by('-created_at')[:50]

    context = {
        'orders': orders,
        'current_status': status_filter,
        'search_query': search_query,
        'status_choices': Order.Status.choices,
        'section': 'orders',
    }
    return render(request, 'staff/orders.html', context)


@staff_required
def order_detail(request, order_number):
    """View full details of a specific order and update status."""
    order = get_object_or_404(
        Order.objects.select_related('user', 'coupon').prefetch_related('items'),
        order_number=order_number,
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.Status.choices):
            order.status = new_status

            # Set timestamps
            now = timezone.now()
            timestamp_map = {
                Order.Status.CONFIRMED: 'confirmed_at',
                Order.Status.PREPARING: 'preparing_at',
                Order.Status.READY: 'ready_at',
                Order.Status.OUT_FOR_DELIVERY: 'out_for_delivery_at',
                Order.Status.DELIVERED: 'completed_at',
                Order.Status.COLLECTED: 'completed_at',
                Order.Status.CANCELLED: 'cancelled_at',
            }
            if new_status in timestamp_map:
                setattr(order, timestamp_map[new_status], now)

            order.save()
            messages.success(
                request,
                f'Order #{order.order_number} status updated to {order.status_label}.',
            )
        return redirect('staff:order_detail', order_number=order.order_number)

    context = {
        'order': order,
        'status_choices': Order.Status.choices,
        'section': 'orders',
    }
    return render(request, 'staff/order_detail.html', context)


# ──────── Menu Management ────────


@staff_required
def menu_list(request):
    """List all menu items with availability and category filters."""
    category_filter = request.GET.get('category', '')
    availability_filter = request.GET.get('availability', '')
    search_query = request.GET.get('q', '').strip()

    items = MenuItem.objects.select_related('category').all()

    if category_filter:
        items = items.filter(category_id=category_filter)

    if availability_filter == 'available':
        items = items.filter(is_available=True)
    elif availability_filter == 'unavailable':
        items = items.filter(is_available=False)

    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    items = items.order_by('category__name', 'sort_order', 'name')
    categories = Category.objects.filter(is_active=True)

    context = {
        'items': items,
        'categories': categories,
        'current_category': category_filter,
        'current_availability': availability_filter,
        'search_query': search_query,
        'section': 'menu',
    }
    return render(request, 'staff/menu_list.html', context)


@staff_required
@require_http_methods(['GET', 'POST'])
def menu_edit(request, item_id=None):
    """Create or edit a menu item."""
    if item_id:
        item = get_object_or_404(MenuItem, id=item_id)
        is_new = False
    else:
        item = MenuItem()
        is_new = True

    categories = Category.objects.filter(is_active=True)

    if request.method == 'POST':
        category_id = request.POST.get('category')
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price')
        is_available = request.POST.get('is_available') == 'on'
        is_featured = request.POST.get('is_featured') == 'on'
        is_vegetarian = request.POST.get('is_vegetarian') == 'on'
        is_vegan = request.POST.get('is_vegan') == 'on'
        is_spicy = request.POST.get('is_spicy') == 'on'
        is_gluten_free = request.POST.get('is_gluten_free') == 'on'
        prep_time = request.POST.get('prep_time_minutes', 15)
        calories = request.POST.get('calories', '')

        errors = []
        if not name:
            errors.append('Item name is required.')
        if not price:
            errors.append('Price is required.')
        if not category_id:
            errors.append('Category is required.')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            item.category_id = category_id
            item.name = name
            item.description = description
            item.price = Decimal(price)
            item.is_available = is_available
            item.is_featured = is_featured
            item.is_vegetarian = is_vegetarian
            item.is_vegan = is_vegan
            item.is_spicy = is_spicy
            item.is_gluten_free = is_gluten_free
            item.prep_time_minutes = int(prep_time)

            if calories:
                item.calories = int(calories)

            if request.FILES.get('image'):
                item.image = request.FILES['image']

            item.save()

            msg = 'Menu item updated.' if not is_new else 'Menu item created.'
            messages.success(request, msg)
            return redirect('staff:menu_list')

    context = {
        'item': item,
        'categories': categories,
        'is_new': is_new,
        'section': 'menu',
    }
    return render(request, 'staff/menu_form.html', context)


@staff_required
@require_POST
def menu_toggle_availability(request, item_id):
    """Toggle menu item availability."""
    item = get_object_or_404(MenuItem, id=item_id)
    item.is_available = not item.is_available
    item.save(update_fields=['is_available'])
    status = 'available' if item.is_available else 'unavailable'
    messages.success(request, f'"{item.name}" is now {status}.')
    return redirect('staff:menu_list')


# ──────── Categories ────────


@staff_required
def category_list(request):
    """List all categories."""
    categories = Category.objects.all().order_by('sort_order', 'name')
    context = {
        'categories': categories,
        'section': 'categories',
    }
    return render(request, 'staff/categories.html', context)


@staff_required
@require_http_methods(['GET', 'POST'])
def category_edit(request, category_id=None):
    """Create or edit a category."""
    if category_id:
        category = get_object_or_404(Category, id=category_id)
        is_new = False
    else:
        category = Category()
        is_new = True

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon', '').strip()
        sort_order = request.POST.get('sort_order', 0)
        is_active = request.POST.get('is_active') == 'on'

        if not name:
            messages.error(request, 'Category name is required.')
        else:
            category.name = name
            category.description = description
            category.icon = icon
            category.sort_order = int(sort_order)
            category.is_active = is_active

            if request.FILES.get('image'):
                category.image = request.FILES['image']

            category.save()
            msg = 'Category updated.' if not is_new else 'Category created.'
            messages.success(request, msg)
            return redirect('staff:category_list')

    context = {
        'category': category,
        'is_new': is_new,
        'section': 'categories',
    }
    return render(request, 'staff/category_form.html', context)


@staff_required
@require_POST
def category_toggle_active(request, category_id):
    """Toggle category active status."""
    category = get_object_or_404(Category, id=category_id)
    category.is_active = not category.is_active
    category.save(update_fields=['is_active'])
    status = 'active' if category.is_active else 'inactive'
    messages.success(request, f'"{category.name}" is now {status}.')
    return redirect('staff:category_list')


# ──────── Coupons / Discounts ────────


@staff_required
def coupon_list(request):
    """List all coupons / promo codes."""
    coupons = Coupon.objects.all().order_by('-created_at')
    context = {
        'coupons': coupons,
        'section': 'coupons',
    }
    return render(request, 'staff/coupons.html', context)


@staff_required
@require_http_methods(['GET', 'POST'])
def coupon_edit(request, coupon_id=None):
    """Create or edit a coupon / promo code."""
    if coupon_id:
        coupon = get_object_or_404(Coupon, id=coupon_id)
        is_new = False
    else:
        coupon = Coupon()
        is_new = True

    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        discount_type = request.POST.get('discount_type', Coupon.DiscountType.PERCENTAGE)
        discount_value = request.POST.get('discount_value')
        min_spend = request.POST.get('min_spend', 0)
        max_uses = request.POST.get('max_uses', 0)
        is_active = request.POST.get('is_active') == 'on'
        valid_from = request.POST.get('valid_from')
        valid_until = request.POST.get('valid_until')

        from django.utils.dateparse import parse_datetime

        errors = []
        if not code:
            errors.append('Coupon code is required.')
        if not discount_value:
            errors.append('Discount value is required.')
        if not valid_from:
            errors.append('Valid from date is required.')
        if not valid_until:
            errors.append('Valid until date is required.')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            coupon.code = code
            coupon.discount_type = discount_type
            coupon.discount_value = Decimal(discount_value)
            coupon.min_spend = Decimal(min_spend)
            coupon.max_uses = int(max_uses)
            coupon.is_active = is_active

            if valid_from:
                coupon.valid_from = parse_datetime(valid_from)
            if valid_until:
                coupon.valid_until = parse_datetime(valid_until)

            coupon.save()
            msg = 'Coupon updated.' if not is_new else 'Coupon created.'
            messages.success(request, msg)
            return redirect('staff:coupon_list')

    context = {
        'coupon': coupon,
        'discount_types': Coupon.DiscountType.choices,
        'is_new': is_new,
        'section': 'coupons',
    }
    return render(request, 'staff/coupon_form.html', context)


@staff_required
@require_POST
def coupon_toggle_active(request, coupon_id):
    """Toggle coupon active status."""
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.is_active = not coupon.is_active
    coupon.save(update_fields=['is_active'])
    status = 'active' if coupon.is_active else 'inactive'
    messages.success(request, f'Coupon "{coupon.code}" is now {status}.')
    return redirect('staff:coupon_list')


# ──────── Reviews ────────


@staff_required
def review_list(request):
    """List all reviews with approval management."""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '').strip()

    reviews = Review.objects.select_related('user', 'menu_item').all()

    if status_filter == 'pending':
        reviews = reviews.filter(is_approved=False)
    elif status_filter == 'approved':
        reviews = reviews.filter(is_approved=True)

    if search_query:
        reviews = reviews.filter(
            Q(user__email__icontains=search_query) |
            Q(menu_item__name__icontains=search_query) |
            Q(comment__icontains=search_query)
        )

    reviews = reviews.order_by('-created_at')[:50]

    if request.method == 'POST':
        review_id = request.POST.get('review_id')
        action = request.POST.get('action')

        review = get_object_or_404(Review, id=review_id)

        if action == 'approve':
            review.is_approved = True
            review.save(update_fields=['is_approved'])
            messages.success(request, f'Review by {review.user.full_name} approved.')
        elif action == 'delete':
            review.delete()
            messages.success(request, 'Review deleted.')

        return redirect('staff:review_list')

    context = {
        'reviews': reviews,
        'current_status': status_filter,
        'search_query': search_query,
        'section': 'reviews',
    }
    return render(request, 'staff/reviews.html', context)


# ──────── Customers ────────


@staff_required
def customer_list(request):
    """List all customers with order stats."""
    search_query = request.GET.get('q', '').strip()

    customers = User.objects.filter(role=User.Role.CUSTOMER).annotate(
        order_count=Count('orders'),
        total_spent=Sum('orders__total', filter=Q(orders__status__in=[
            Order.Status.DELIVERED, Order.Status.COLLECTED,
        ])),
    )

    if search_query:
        customers = customers.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    customers = customers.order_by('-created_at')[:100]

    context = {
        'customers': customers,
        'search_query': search_query,
        'section': 'customers',
    }
    return render(request, 'staff/customers.html', context)


@staff_required
def customer_detail(request, customer_id):
    """View customer details and their orders."""
    customer = get_object_or_404(User, id=customer_id, role=User.Role.CUSTOMER)
    orders = Order.objects.filter(user=customer).prefetch_related('items').order_by('-created_at')[:20]

    # Stats
    total_orders = orders.count()
    completed_orders = orders.filter(
        status__in=[Order.Status.DELIVERED, Order.Status.COLLECTED]
    ).count()
    total_spent = orders.filter(
        status__in=[Order.Status.DELIVERED, Order.Status.COLLECTED]
    ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    context = {
        'customer': customer,
        'orders': orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_spent': total_spent,
        'section': 'customers',
    }
    return render(request, 'staff/customer_detail.html', context)

