# users/middleware.py

from django.conf import settings
from django.shortcuts import redirect
from .models import User

class TelegramAuthMiddleware:
    """
    Если в session нет 'telegram_id', перенаправляем на /telegram_login/.
    Исключаем пути: /telegram_login/, /admin/ и /static/.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Пути, на которые не нужно авторизовываться
        exempt_urls = ["/telegram_login/", "/admin/", "/static/"]
        for url in exempt_urls:
            if request.path.startswith(url):
                return self.get_response(request)

        # Тестовый режим (только в DEBUG + ?test_mode=1) – создаём фиктивного пользователя
        if settings.DEBUG and request.GET.get("test_mode") == "1":
            test_id = 12345678
            try:
                test_user = User.objects.get(telegram_id=test_id)
            except User.DoesNotExist:
                test_user = User(
                    telegram_id=test_id,
                    username="test_user",
                    first_name="Test",
                    last_name="User"
                )
                test_user.save()
                from trees.models import Tree
                Tree.objects.create(user=test_user, type="CF")
            request.user = test_user
            request.session["telegram_id"] = test_id
            return self.get_response(request)

        # Основная логика: проверяем, есть ли telegram_id в сессии
        telegram_id = request.session.get("telegram_id")
        if not telegram_id:
            # Если нет – сразу редиректим на страницу авторизации через WebApp
            return redirect("/telegram_login/")

        # Если же есть, пробуем загрузить соответствующего пользователя
        try:
            user = User.objects.get(telegram_id=telegram_id)
            request.user = user
        except User.DoesNotExist:
            # Если вдруг в сессии лежит несуществующий ID, сбрасываем сессию и снова кидаем на авторизацию
            del request.session["telegram_id"]
            return redirect("/telegram_login/")

        # Всё ок – продолжаем
        return self.get_response(request)
