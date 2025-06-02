from django.urls import path
from . import views
from .views import buy_ton_tree

app_name = 'shop'

urlpatterns = [
    path('', views.shop, name='shop'),
    path('buy/<int:item_id>/', views.buy_item, name='buy_item'),
    path("buy_ton_tree/", buy_ton_tree, name="buy_ton_tree"),
] 