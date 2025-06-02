from django.urls import path, include
from . import views

app_name = 'p2p'

urlpatterns = [
    # Веб-интерфейс
    path('', views.p2p_market, name='market'),
    path('orders/create/', views.create_order, name='create_order'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/buy/', views.buy_order, name='buy_order'),
    path('orders/<int:order_id>/cancel/', views.toggle_order, name='cancel_order'),
    path('my/orders/', views.p2p_market, name='my_orders'),  # Перенаправляем на главную страницу с фильтром
    path('my/transactions/', views.p2p_market, name='my_transactions'),  # Перенаправляем на главную страницу с фильтром
    path('transactions/<int:deal_id>/', views.deal_detail, name='transaction_detail'),
    path('transactions/<int:transaction_id>/confirm-payment/', views.toggle_order, name='confirm_payment'),  # Использует похожую функцию
    path('transactions/<int:transaction_id>/confirm-receipt/', views.toggle_order, name='confirm_receipt'),  # Использует похожую функцию
    path('transactions/<int:deal_id>/message/', views.send_message, name='send_message'),
    
    # API
    path('api/', include('p2p.api.urls')),
] 