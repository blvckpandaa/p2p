from django.urls import path
from . import views

urlpatterns = [
    path('', views.staking, name='staking'),
    path('create/', views.create_staking, name='create_staking'),
    path('claim/<int:staking_id>/', views.claim_staking, name='claim_staking'),
] 