from django.urls import path
from . import views

urlpatterns = [
    path('', views.shop, name='shop'),
    path('buy/<int:item_id>/', views.buy_item, name='buy_item'),
] 