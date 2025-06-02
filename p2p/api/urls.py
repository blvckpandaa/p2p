from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .views import OrderViewSet, TransactionViewSet, MessageViewSet

# Создаем основной роутер
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'transactions', TransactionViewSet, basename='transaction')

# Создаем вложенный роутер для сообщений в транзакциях
transactions_router = NestedDefaultRouter(router, r'transactions', lookup='transaction')
transactions_router.register(r'messages', MessageViewSet, basename='transaction-message')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(transactions_router.urls)),
] 