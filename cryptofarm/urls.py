"""
URL configuration for cryptofarm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from users.views import ton_manifest

urlpatterns = [
    path('tonconnect-manifest.json', ton_manifest, name='ton-manifest'),
    path('admin/', admin.site.urls),
    path('', include('trees.urls')),  # Главная страница с деревьями
    path('shop/', include('shop.urls')),
    path('p2p/', include('p2p.urls')),
    path('referral/', include('referrals.urls')),
    path('staking/', include('staking.urls')),
    path('telegram_login/', include("users.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
