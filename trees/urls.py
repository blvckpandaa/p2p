from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('tree/', views.tree_list, name='tree_list'),
    path('tree/create/', views.create_tree, name='create_tree'),
    path('tree/<int:tree_id>/', views.tree_detail, name='tree_detail'),
    path('tree/<int:tree_id>/water/', views.water_tree, name='water_tree'),
    path('tree/<int:tree_id>/upgrade/', views.upgrade_tree, name='upgrade_tree'),
    path('tree/<int:tree_id>/collect/', views.collect_income, name='collect_income'),
]