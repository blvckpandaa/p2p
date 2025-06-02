from django.urls import path
from . import views

urlpatterns = [
    path('', views.referral_program, name='referral_program'),
] 