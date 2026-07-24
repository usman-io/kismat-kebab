from django.contrib import admin

from .models import (
    Cart, CartItem, Category, Coupon, ExtraGroup, ExtraOption,
    FavouriteItem, MenuItem, MenuItemExtraGroup, Order, OrderItem, Review,
)


class ExtraOptionInline(admin.TabularInline):
    model = ExtraOption
    extra = 1
    fields = ('name', 'price', 'is_available', 'is_default', 'sort_order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order', 'is_active', 'item_count_display')
    list_editable = ('sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='Items')
    def item_count_display(self, obj):
        return obj.item_count


class MenuItemExtraGroupInline(admin.TabularInline):
    model = MenuItemExtraGroup
    extra = 1
    autocomplete_fields = ('extra_group',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'price', 'is_available', 'is_featured',
        'is_vegetarian', 'is_spicy', 'sort_order',
    )
    list_editable = ('price', 'is_available', 'is_featured', 'sort_order')
    list_filter = (
        'category', 'is_available', 'is_featured',
        'is_vegetarian', 'is_vegan', 'is_spicy', 'is_gluten_free',
    )
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MenuItemExtraGroupInline]
    fieldsets = (
        (None, {
            'fields': ('category', 'name', 'slug', 'description', 'price', 'image'),
        }),
        ('Availability & display', {
            'fields': ('is_available', 'is_featured', 'sort_order', 'prep_time_minutes', 'calories'),
        }),
        ('Dietary', {
            'fields': ('is_vegetarian', 'is_vegan', 'is_spicy', 'is_gluten_free'),
        }),
    )


@admin.register(ExtraGroup)
class ExtraGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_selections', 'max_selections', 'is_required', 'sort_order')
    list_editable = ('sort_order', 'is_required')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ExtraOptionInline]


@admin.register(ExtraOption)
class ExtraOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'price', 'is_available', 'is_default', 'sort_order')
    list_editable = ('price', 'is_available', 'sort_order')
    list_filter = ('group', 'is_available')
    search_fields = ('name', 'group__name')


@admin.register(MenuItemExtraGroup)
class MenuItemExtraGroupAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'extra_group', 'sort_order')
    list_filter = ('extra_group', 'menu_item__category')
    autocomplete_fields = ('menu_item', 'extra_group')


# ──────── New model admin registrations ────────


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('menu_item', 'quantity', 'extras_data', 'total_price')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'item_count_display', 'subtotal_display', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('user__email', 'session_key')
    readonly_fields = ('session_key', 'created_at', 'updated_at')
    inlines = [CartItemInline]

    @admin.display(description='Items')
    def item_count_display(self, obj):
        return obj.item_count

    @admin.display(description='Subtotal')
    def subtotal_display(self, obj):
        return f'£{obj.subtotal:.2f}'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_spend', 'current_uses', 'max_uses', 'is_active', 'valid_from', 'valid_until')
    list_editable = ('is_active',)
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('menu_item_name', 'menu_item_price', 'quantity', 'extras_data', 'unit_price', 'total_price')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user_email', 'order_type', 'status', 'total', 'created_at')
    list_filter = ('status', 'order_type', 'created_at')
    search_fields = ('order_number', 'user__email', 'delivery_name')
    readonly_fields = (
        'order_number', 'subtotal', 'discount_amount', 'delivery_fee', 'total',
        'created_at', 'confirmed_at', 'preparing_at', 'ready_at',
        'out_for_delivery_at', 'completed_at', 'cancelled_at',
    )
    inlines = [OrderItemInline]

    @admin.display(description='Customer')
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Guest'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'user', 'rating', 'is_approved', 'created_at')
    list_editable = ('is_approved',)
    list_filter = ('is_approved', 'rating', 'menu_item')
    search_fields = ('menu_item__name', 'user__email', 'comment')


@admin.register(FavouriteItem)
class FavouriteItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'menu_item', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'menu_item__name')
