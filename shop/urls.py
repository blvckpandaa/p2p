from django.urls import path
from . import views
from .views import buy_ton_tree

app_name = 'shop'

urlpatterns = [
    path('', views.shop, name='shop'),
    path('buy/<int:item_id>/', views.buy_shop_item, name='buy_shop_item'),
    path('use/<int:purchase_id>/', views.use_shop_item, name='use_shop_item'),
    path('buy/branches/', views.buy_branches, name='buy_branches'),
    path("buy_ton_tree/", buy_ton_tree, name="buy_ton_tree"),
]
