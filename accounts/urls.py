from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify/sent/', views.verify_email_sent, name='verify_email_sent'),
    path('verify/resend/', views.resend_verification, name='resend_verification'),
    path('verify/<uuid:token>/', views.verify_email, name='verify_email'),
    path('profile/', views.profile, name='profile'),
]
