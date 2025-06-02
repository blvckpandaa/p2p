# trees/views.py

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Tree
from users.models import User as TelegramUser

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

def tree_detail(request, tree_id):
    user = get_current_user(request)
    if not user:
        return render(request, "not_authenticated.html")

    tree = get_object_or_404(Tree, id=tree_id, user=user)
    return render(request, "tree/detail.html", {
        "tree": tree,
        "user": user,
        "is_watered": tree.is_watered(),
        "is_fertilized": tree.is_fertilized(),
        "can_upgrade": tree.can_upgrade()
    })

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
