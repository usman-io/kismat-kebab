from django.urls import path

from . import views

app_name = 'staff'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),

    # Menu management
    path('menu/', views.menu_list, name='menu_list'),
    path('menu/add/', views.menu_edit, name='menu_add'),
    path('menu/<int:item_id>/edit/', views.menu_edit, name='menu_edit'),
    path('menu/<int:item_id>/toggle-availability/', views.menu_toggle_availability, name='menu_toggle_availability'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_edit, name='category_add'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:category_id>/toggle/', views.category_toggle_active, name='category_toggle_active'),

    # Coupons / Discounts
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/add/', views.coupon_edit, name='coupon_add'),
    path('coupons/<int:coupon_id>/edit/', views.coupon_edit, name='coupon_edit'),
    path('coupons/<int:coupon_id>/toggle/', views.coupon_toggle_active, name='coupon_toggle_active'),

    # Reviews
    path('reviews/', views.review_list, name='review_list'),

    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<int:customer_id>/', views.customer_detail, name='customer_detail'),
]

