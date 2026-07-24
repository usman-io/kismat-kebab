from django.db.models import Avg, Count, Q

from .models import Category, MenuItem


def get_active_categories():
    return Category.objects.filter(is_active=True).prefetch_related('items')


def get_menu_items_with_ratings(queryset):
    """Annotate menu items with average rating and review count."""
    return queryset.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
    )


def filter_menu_items(queryset, params):
    """Apply search and dietary filters from GET params."""
    q = params.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(description__icontains=q),
        )

    if params.get('vegetarian') == '1':
        queryset = queryset.filter(is_vegetarian=True)
    if params.get('vegan') == '1':
        queryset = queryset.filter(is_vegan=True)
    if params.get('spicy') == '1':
        queryset = queryset.filter(is_spicy=True)
    if params.get('gluten_free') == '1':
        queryset = queryset.filter(is_gluten_free=True)

    sort = params.get('sort', 'default')
    if sort == 'price_low':
        queryset = queryset.order_by('price', 'name')
    elif sort == 'price_high':
        queryset = queryset.order_by('-price', 'name')
    elif sort == 'name':
        queryset = queryset.order_by('name')
    else:
        queryset = queryset.order_by('sort_order', 'name')

    return queryset


def get_menu_items(params, category=None):
    queryset = MenuItem.objects.filter(is_available=True).select_related('category')
    if category:
        queryset = queryset.filter(category=category)
    elif category_slug := params.get('category'):
        queryset = queryset.filter(category__slug=category_slug, category__is_active=True)
    queryset = get_menu_items_with_ratings(queryset)
    return filter_menu_items(queryset, params)


def get_filter_state(params):
    """Return current filter values for template re-population."""
    return {
        'q': params.get('q', ''),
        'category': params.get('category', ''),
        'vegetarian': params.get('vegetarian') == '1',
        'vegan': params.get('vegan') == '1',
        'spicy': params.get('spicy') == '1',
        'gluten_free': params.get('gluten_free') == '1',
        'sort': params.get('sort', 'default'),
    }
