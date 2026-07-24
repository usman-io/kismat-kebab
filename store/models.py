import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    """Menu category — Burgers, Pizzas, Kebabs, etc."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, blank=True, help_text='Emoji icon fallback')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:category', kwargs={'slug': self.slug})

    @property
    def item_count(self):
        return self.items.filter(is_available=True).count()


class MenuItem(models.Model):
    """Individual food item on the menu."""

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='items',
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='menu/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_spicy = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    prep_time_minutes = models.PositiveSmallIntegerField(default=15)
    calories = models.PositiveIntegerField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while MenuItem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:menu_item', kwargs={'slug': self.slug})

    @property
    def display_price(self):
        return f'£{self.price:.2f}'

    @property
    def dietary_tags(self):
        tags = []
        if self.is_vegan:
            tags.append(('Vegan', 'tag-vegan'))
        elif self.is_vegetarian:
            tags.append(('Vegetarian', 'tag-veg'))
        if self.is_spicy:
            tags.append(('Spicy', 'tag-spicy'))
        if self.is_gluten_free:
            tags.append(('Gluten Free', 'tag-gf'))
        return tags


class ExtraGroup(models.Model):
    """
    Group of extras/toppings — e.g. 'Choose Size', 'Extra Toppings'.
    Linked to menu items via MenuItemExtraGroup.
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    min_selections = models.PositiveSmallIntegerField(
        default=0,
        help_text='Minimum options customer must pick (0 = optional group).',
    )
    max_selections = models.PositiveSmallIntegerField(
        default=1,
        help_text='Maximum options allowed (0 = unlimited).',
    )
    is_required = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while ExtraGroup.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def selection_label(self):
        if self.max_selections == 1:
            return 'Choose one'
        if self.max_selections == 0:
            return 'Choose any'
        return f'Choose up to {self.max_selections}'


class ExtraOption(models.Model):
    """Single extra/topping choice within a group."""

    group = models.ForeignKey(
        ExtraGroup,
        on_delete=models.CASCADE,
        related_name='options',
    )
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    is_available = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        unique_together = [['group', 'name']]

    def __str__(self):
        return f'{self.name} ({self.group.name})'

    @property
    def display_price(self):
        if self.price == 0:
            return 'Free'
        return f'+£{self.price:.2f}'


class MenuItemExtraGroup(models.Model):
    """Links extra groups to specific menu items."""

    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='extra_groups',
    )
    extra_group = models.ForeignKey(
        ExtraGroup,
        on_delete=models.CASCADE,
        related_name='menu_items',
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']
        unique_together = [['menu_item', 'extra_group']]

    def __str__(self):
        return f'{self.menu_item.name} — {self.extra_group.name}'


class Coupon(models.Model):
    """Discount coupon for orders."""

    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage (%)'
        FIXED = 'fixed', 'Fixed Amount (£)'

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
    )
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    min_spend = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    max_uses = models.PositiveIntegerField(default=0, help_text='0 = unlimited')
    current_uses = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.code} ({self.get_discount_type_display()})'

    @property
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False
        if self.max_uses > 0 and self.current_uses >= self.max_uses:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        return True

    def calculate_discount(self, subtotal):
        """Calculate discount amount based on subtotal."""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return (subtotal * self.discount_value) / Decimal('100.00')
        return min(self.discount_value, subtotal)

    def increment_usage(self):
        self.current_uses += 1
        self.save(update_fields=['current_uses'])


class Cart(models.Model):
    """Shopping cart — session-based for guests, user-linked for logged-in customers."""

    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart',
    )
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        owner = self.user.email if self.user else self.session_key
        return f'Cart ({owner})'

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def discount_amount(self):
        if self.coupon and self.coupon.is_valid:
            return self.coupon.calculate_discount(self.subtotal)
        return Decimal('0.00')

    @property
    def total(self):
        return max(self.subtotal - self.discount_amount, Decimal('0.00'))

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    def get_or_create_cart(self, request):
        """Get existing cart or create a new one for the current session/user."""
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
            # Merge any session-based cart into user cart
            session_key = request.session.session_key
            if session_key:
                session_cart = Cart.objects.filter(session_key=session_key).exclude(user=request.user).first()
                if session_cart:
                    for session_item in session_cart.items.all():
                        cart_item, item_created = CartItem.objects.get_or_create(
                            cart=cart,
                            menu_item=session_item.menu_item,
                            defaults={'quantity': session_item.quantity, 'extras_data': session_item.extras_data},
                        )
                        if not item_created:
                            cart_item.quantity += session_item.quantity
                            cart_item.save()
                    session_cart.delete()
            return cart
        else:
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
            cart, created = Cart.objects.get_or_create(session_key=session_key)
            return cart


class CartItem(models.Model):
    """Individual item in a shopping cart, including selected extras."""

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='cart_items',
    )
    quantity = models.PositiveIntegerField(default=1)
    extras_data = models.JSONField(
        default=list,
        blank=True,
        help_text='List of selected extra option IDs',
    )
    special_instructions = models.TextField(blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        unique_together = [['cart', 'menu_item']]

    def __str__(self):
        return f'{self.quantity}x {self.menu_item.name}'

    @property
    def selected_extras(self):
        """Return list of ExtraOption objects from stored IDs."""
        if not self.extras_data:
            return []
        return ExtraOption.objects.filter(id__in=self.extras_data, is_available=True)

    @property
    def extras_total(self):
        return sum(opt.price for opt in self.selected_extras)

    @property
    def unit_price(self):
        return self.menu_item.price + self.extras_total

    @property
    def total_price(self):
        return self.unit_price * self.quantity


class Order(models.Model):
    """Customer order with delivery/collection and status tracking."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        PREPARING = 'preparing', 'Preparing'
        READY = 'ready', 'Ready'
        OUT_FOR_DELIVERY = 'out_for_delivery', 'Out for Delivery'
        DELIVERED = 'delivered', 'Delivered'
        COLLECTED = 'collected', 'Collected'
        CANCELLED = 'cancelled', 'Cancelled'

    class OrderType(models.TextChoices):
        DELIVERY = 'delivery', 'Delivery'
        COLLECTION = 'collection', 'Collection'

    order_number = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)
    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        default=OrderType.DELIVERY,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Delivery details
    delivery_name = models.CharField(max_length=200, blank=True)
    delivery_phone = models.CharField(max_length=20, blank=True)
    delivery_address = models.TextField(blank=True)
    delivery_postcode = models.CharField(max_length=10, blank=True)
    delivery_notes = models.TextField(blank=True)

    # Financials
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Coupon used
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )

    # Stripe payment
    stripe_payment_intent_id = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='Stripe PaymentIntent ID for this order',
    )
    is_paid = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    preparing_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.order_number}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        from datetime import datetime
        from random import randint
        date_part = datetime.now().strftime('%Y%m%d')
        rand_part = f'{randint(1000, 9999)}'
        return f'QT-{date_part}-{rand_part}'

    @property
    def status_label(self):
        labels = {
            self.Status.PENDING: 'Awaiting Confirmation',
            self.Status.CONFIRMED: 'Order Confirmed',
            self.Status.PREPARING: 'Being Prepared',
            self.Status.READY: 'Ready',
            self.Status.OUT_FOR_DELIVERY: 'Out for Delivery',
            self.Status.DELIVERED: 'Delivered',
            self.Status.COLLECTED: 'Collected',
            self.Status.CANCELLED: 'Cancelled',
        }
        return labels.get(self.status, self.status)

    @property
    def status_percentage(self):
        """
        Return progress percentage for the customer-facing tracking timeline.
        Sequence: confirmed -> preparing -> ready -> out_for_delivery -> delivered/collected
        Pending and Cancelled both show 0%.
        """
        tracking_sequence = [
            self.Status.CONFIRMED,
            self.Status.PREPARING,
            self.Status.READY,
            self.Status.OUT_FOR_DELIVERY,
            self.Status.DELIVERED,
            self.Status.COLLECTED,
        ]
        if self.status in tracking_sequence:
            idx = tracking_sequence.index(self.status)
            max_idx = len(tracking_sequence) - 1
            return int((idx / max_idx) * 100)
        return 0

    @property
    def is_cancellable(self):
        return self.status in [self.Status.PENDING, self.Status.CONFIRMED]

    @property
    def can_reorder(self):
        return self.status in [
            self.Status.DELIVERED, self.Status.COLLECTED, self.Status.CANCELLED
        ]


class OrderItem(models.Model):
    """Individual item within an order."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items',
    )
    menu_item_name = models.CharField(max_length=200)
    menu_item_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    extras_data = models.JSONField(
        default=list,
        blank=True,
        help_text='Snapshot of selected extras: [{"name": "Cheese", "price": "1.50"}, ...]',
    )
    extras_total = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity}x {self.menu_item_name}'


class Review(models.Model):
    """Customer review/rating for a menu item."""

    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        help_text='Rating from 1 to 5 stars',
    )
    comment = models.TextField(blank=True, max_length=1000)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['menu_item', 'user', 'order']]

    def __str__(self):
        return f'{self.user.email} — {self.menu_item.name} ({self.rating}★)'


class FavouriteItem(models.Model):
    """User's favourite/saved menu items for quick reorder."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favourite_items',
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='favourited_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'menu_item']]
        verbose_name_plural = 'favourite items'

    def __str__(self):
        return f'{self.user.email} ♥ {self.menu_item.name}'
