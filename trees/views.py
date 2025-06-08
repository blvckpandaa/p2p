# trees/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import Tree
from users.models import User as TelegramUser
from django.utils import timezone
from django.conf import settings

def get_current_user(request):
    """
    Если в сессии есть telegram_id, возвращаем User,
    иначе — None.
    """
    tg_id = request.session.get("telegram_id")
    if not tg_id:
        return None
    try:
        return TelegramUser.objects.get(telegram_id=tg_id)
    except TelegramUser.DoesNotExist:
        return None

def home(request):
    """
    1) Пытаемся взять пользователя из сессии.
    2) Если нет user — рендерим not_authenticated.html.
    3) Если user есть — выводим его деревья (или создаём первое).
    """
    user = get_current_user(request)
    if not user:
        return render(request, "not_authenticated.html")

    # Получаем все деревья пользователя:
    trees = Tree.objects.filter(user=user)
    if not trees.exists():
        Tree.objects.create(user=user, type="CF")
        trees = Tree.objects.filter(user=user)

    return render(request, "home.html", {
        "trees": trees,
        "user": user
    })

def tree_list(request):
    """
    Отображает список всех деревьев пользователя.
    Если пользователь не авторизован, перенаправляет на страницу авторизации.
    """
    user = get_current_user(request)
    if not user:
        return render(request, "not_authenticated.html")

    # Получаем все деревья пользователя
    trees = Tree.objects.filter(user=user)
    
    # Если у пользователя нет деревьев, создаем первое дерево
    if not trees.exists():
        Tree.objects.create(user=user, type="CF")
        trees = Tree.objects.filter(user=user)

    return render(request, "tree/list.html", {
        "trees": trees,
        "user": user
    })

def tree_detail(request, tree_id):
    user = get_current_user(request)
    if not user:
        return render(request, "not_authenticated.html")

    tree = get_object_or_404(Tree, id=tree_id, user=user)
    
    # Расчет дополнительных параметров для отображения
    context = {
        "tree": tree,
        "user": user,
        "is_watered": tree.is_watered(),
        "is_fertilized": tree.is_fertilized(),
        "can_upgrade": tree.can_upgrade()
    }
    
    # Добавляем параметры для отображения в шаблоне
    context["tree_type"] = tree.type.lower()
    context["crypto_type"] = tree.type.lower()
    context["water_cost"] = 5  # стоимость полива
    context["branch_cost"] = 10  # стоимость сбора ветки
    
    # Проверка статуса автополива
    context["auto_water_enabled"] = False
    context["auto_water_remaining"] = 0
    
    if tree.auto_water_until and tree.auto_water_until > timezone.now():
        context["auto_water_enabled"] = True
        time_diff = tree.auto_water_until - timezone.now()
        context["auto_water_remaining"] = int(time_diff.total_seconds() / 3600) + 1
    
    # Проверка статуса удобрения
    context["fertilizer_active"] = False
    context["fertilizer_remaining"] = 0
    
    if tree.fertilized_until and tree.fertilized_until > timezone.now():
        context["fertilizer_active"] = True
        time_diff = tree.fertilized_until - timezone.now()
        context["fertilizer_remaining"] = int(time_diff.total_seconds() / 3600) + 1
    
    # Уровень воды (для прогресс-бара)
    water_level = 0
    if tree.is_watered():
        watering_duration = settings.GAME_SETTINGS.get('WATERING_DURATION', 5)
        time_since_watering = timezone.now() - tree.last_watered
        elapsed_percent = (time_since_watering.total_seconds() / (watering_duration * 3600)) * 100
        water_level = max(0, 100 - elapsed_percent)
    
    context["water_level"] = int(water_level)
    
    return render(request, "tree/detail.html", context)

def water_tree(request, tree_id):
    user = get_current_user(request)
    if not user:
        return JsonResponse({"status": "error", "message": "Сначала авторизуйтесь"}, status=403)

    tree = get_object_or_404(Tree, id=tree_id, user=user)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Требуется метод POST"}, status=400)

    branch_dropped = tree.water()
    response_data = {
        "status": "success",
        "message": "Дерево успешно полито",
        "is_watered": True,
        "branch_dropped": branch_dropped,
        "branches_collected": tree.branches_collected
    }
    if branch_dropped:
        response_data["message"] += ". Вы нашли новую ветку!"
    return JsonResponse(response_data)

def upgrade_tree(request, tree_id):
    user = get_current_user(request)
    if not user:
        return JsonResponse({"status": "error", "message": "Сначала авторизуйтесь"}, status=403)

    tree = get_object_or_404(Tree, id=tree_id, user=user)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Требуется метод POST"}, status=400)

    if not tree.can_upgrade():
        return JsonResponse({
            "status": "error",
            "message": "Недостаточно веток для улучшения. Накопите ещё веток."
        }, status=400)

    tree.upgrade()
    return JsonResponse({
        "status": "success",
        "message": f"Дерево улучшено до уровня {tree.level}",
        "new_level": tree.level,
        "new_income": tree.income_per_hour
    })

def collect_income(request, tree_id):
    """Собирает доход с дерева и начисляет его на баланс пользователя"""
    user = get_current_user(request)
    if not user:
        return JsonResponse({"status": "error", "message": "Сначала авторизуйтесь"}, status=403)

    tree = get_object_or_404(Tree, id=tree_id, user=user)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Требуется метод POST"}, status=400)
    
    # Проверяем, полито ли дерево
    if not tree.is_watered():
        return JsonResponse({"status": "error", "message": "Дерево нужно сначала полить"}, status=400)
    
    # Рассчитываем доход (базовый доход с учетом удобрений)
    income = tree.get_current_income()
    
    # Начисляем токены пользователю в зависимости от типа дерева
    if tree.type == "CF":
        user.cf_balance += income
    elif tree.type == "TON":
        user.ton_balance += income
    
    # Сохраняем изменения
    user.save()
    
    # Отмечаем дерево как "не политое" для необходимости нового полива
    tree.last_watered = None
    tree.save()
    
    # Определяем тип токена для сообщения
    token_type = tree.type
    
    return JsonResponse({
        "status": "success",
        "message": f"Собрано {income} {token_type}",
        "income": income,
        "new_balance": user.cf_balance if tree.type == "CF" else user.ton_balance
    })

def create_tree(request):
    """
    Создает новое дерево для пользователя.
    Пользователь может выбрать тип дерева: CF или TON.
    """
    user = get_current_user(request)
    if not user:
        return render(request, "not_authenticated.html")
    
    # Если это GET-запрос, показываем форму создания дерева
    if request.method == "GET":
        return render(request, "tree/create.html", {"user": user})
    
    # Если это POST-запрос, создаем новое дерево
    if request.method == "POST":
        tree_type = request.POST.get("tree_type", "CF")  # По умолчанию CF
        
        # Проверяем, что тип дерева допустимый
        if tree_type not in ["CF", "TON"]:
            tree_type = "CF"  # Если недопустимый тип, используем CF по умолчанию
        
        # Создаем новое дерево
        new_tree = Tree.objects.create(
            user=user,
            type=tree_type
        )
        
        # Перенаправляем на страницу созданного дерева
        return redirect('tree_detail', tree_id=new_tree.id)
    
    # Если запрос не GET и не POST, возвращаем ошибку
    return JsonResponse({"status": "error", "message": "Метод не поддерживается"}, status=405)
