from django.urls import path
from . import views

urlpatterns = [
    path('', views.shop, name='shop'),
    path('buy/<int:item_id>/', views.buy_item, name='buy_item'),
    path('buy/tree/<str:tree_type>/', views.buy_tree, name='buy_tree'),
] 