from django.urls import path
from . import views

urlpatterns = [
    path("", views.telegram_login, name="telegram_login"),
    path('profile/', views.profile_view, name='profile'),
] 