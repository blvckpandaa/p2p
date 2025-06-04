from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('tree/<int:tree_id>/', views.tree_detail, name='tree_detail'),
    path('tree/<int:tree_id>/water/', views.water_tree, name='water_tree'),
    path('tree/<int:tree_id>/upgrade/', views.upgrade_tree, name='upgrade_tree'),
path('tree/<int:tree_id>/collect_income/', views.collect_income, name='collect_income'),
path('use-purchase/<int:purchase_id>/', views.use_shop_item, name='use_shop_item')

] 