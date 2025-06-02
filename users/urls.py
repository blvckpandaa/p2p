from django.urls import path
from .views import *

urlpatterns = [
    path("", telegram_login, name="telegram_login"),
] 