from django.urls import path

from . import views

app_name = 'store'

urlpatterns = [
    # Menu
    path('', views.home, name='home'),
    path('menu/', views.menu_list, name='menu'),
    path('menu/category/<slug:slug>/', views.category_detail, name='category'),
    path('menu/item/<slug:slug>/', views.menu_item_detail, name='menu_item'),

    # Cart
    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/update/', views.update_cart_view, name='update_cart'),
    path('cart/remove/', views.remove_from_cart_view, name='remove_from_cart'),

    # Coupons
    path('cart/coupon/apply/', views.apply_coupon_view, name='apply_coupon'),
    path('cart/coupon/remove/', views.remove_coupon_view, name='remove_coupon'),

    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('order/confirmation/<str:order_number>/', views.order_confirmation, name='order_confirmation'),

    # Orders
    path('order/<str:order_number>/', views.order_detail, name='order_detail'),
    path('order/<str:order_number>/tracking/', views.order_tracking, name='order_tracking'),
    path('order/<str:order_number>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/<str:order_number>/repeat/', views.repeat_order, name='repeat_order'),
    path('orders/', views.order_history, name='order_history'),

    # Reviews
    path('review/add/', views.add_review, name='add_review'),
    path('order/<str:order_number>/review/', views.add_order_review, name='add_order_review'),

    # Stripe payment webhook
    path('payment/webhook/', views.stripe_webhook, name='stripe_webhook'),

    # Favourites
    path('favourites/', views.favourite_list, name='favourites'),
    path('favourites/toggle/', views.toggle_favourite, name='toggle_favourite'),
]

