from django.urls import path
from . import views
from .views import ton_manifest, TonPaymentTestAPI

urlpatterns = [
    path('tonconnect-manifest.json', ton_manifest, name='ton-manifest'),

    # 2) Админ

    path("", views.telegram_login, name="telegram_login"),
    path('profile/', views.profile_view, name='profile'),
    path('deposit_ton/', views.deposit_ton, name='deposit_ton'),
    path('api/ton-payment-test/', TonPaymentTestAPI.as_view(), name='ton-payment-test'),

]