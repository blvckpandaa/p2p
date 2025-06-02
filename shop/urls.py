from django.urls import path
from . import views
from .views import buy_ton_tree

app_name = 'shop'

urlpatterns = [
    path('', views.shop, name='shop'),
    path('shop/buy/auto_water/', views.buy_auto_water, name='buy_auto_water'),
    path('shop/buy/fertilizer/', views.buy_fertilizer, name='buy_fertilizer'),
    path('shop/buy/branches/', views.buy_branches, name='buy_branches'),
    path("buy_ton_tree/", buy_ton_tree, name="buy_ton_tree"),
] 