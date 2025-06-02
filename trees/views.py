# trees/views.py

from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone

from .models import Tree, TonDistribution
from users.models import User as TelegramUser

# Если у вас в проекте есть модель для логов, раскомментируйте импорт и используйте её.
# from .models import TreeLog


def get_current_user(request):
    """
    Возвращает текущего залогиненного TelegramUser по session['telegram_id'].
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
    Главная страница: показывает CF- и TON-деревья пользователя.
    """
    user = get_current_user(request)
    if not user:
        # Если пользователь не залогинен — отдаём шаблон с предложением авторизоваться.
        return render(request, "not_authenticated.html")

    # --- CF-деревья ---
    cf_trees = Tree.objects.filter(user=user, type="CF")
    if not cf_trees.exists():

        Tree.objects.create(user=user, type="CF")
        cf_trees = Tree.objects.filter(user=user, type="CF")

    # --- TON-деревья ---
    ton_trees = Tree.objects.filter(user=user, type="TON")

    # Текущая активная раздача TON (самая «поздняя» с is_active=True)
    active_distribution = TonDistribution.objects.filter(is_active=True).last()

    # Считаем, сколько пользователей участвуют в TON-раздаче (те, у кого есть хотя бы одно TON-дерево)
    participants_count = (
        TelegramUser.objects.filter(trees__type="TON").distinct().count()
    ) or 0

    # Если есть активная раздача и есть участники, считаем, сколько TON выдаётся
    # одному участнику за 1 час.
    ton_per_hour_per_user = None
    if active_distribution and participants_count > 0:
        total_per_user = (active_distribution.total_amount / Decimal(participants_count))
        ton_per_hour_per_user = (total_per_user / Decimal(active_distribution.duration_hours))

    return render(request, "home.html", {
        "user": user,
        "cf_trees": cf_trees,
        "ton_trees": ton_trees,
        "active_distribution": active_distribution,
        "participants_count": participants_count,
        "ton_per_hour_per_user": ton_per_hour_per_user,
    })


def tree_detail(request, tree_id):
    """
    Детали конкретного дерева (CF или TON).
    Для CF: передаем в шаблон is_watered, is_fertilized, can_upgrade, tree_logs.
    Для TON: дополнительно передаем данные о раздаче TON.
    """
    user = get_current_user(request)
    if not user:
        return render(request, "not_authenticated.html")

    tree = get_object_or_404(Tree, id=tree_id, user=user)

    # Проверяем, полито ли дерево (метод is_watered возвращает True/False)
    is_watered = tree.is_watered()
    # Проверяем, активно ли удобрение (для CF)
    is_fertilized = tree.is_fertilized()
    # Проверяем, можно ли апгрейдить (достаточно ли веток)
    can_upgrade = tree.can_upgrade()

    # Базовый контекст
    context = {
        "user": user,
        "tree": tree,
        "is_watered": is_watered,
        "is_fertilized": is_fertilized,
        "can_upgrade": can_upgrade,
    }

    # --- Логи дерева ---
    # Если у вас есть модель TreeLog, например:
    # tree_logs = TreeLog.objects.filter(tree=tree).order_by("-created_at")[:20]
    # И раскомментируйте строку выше и добавьте 'tree_logs': tree_logs в контекст.
    #
    # Если логов нет или модели нет — передаём пустой список:
    tree_logs = []
    context["tree_logs"] = tree_logs

    # --- Данные для TON-дерева ---
    if tree.type == "TON":
        active_dist = TonDistribution.objects.filter(is_active=True).last()
        participants_count = (
            TelegramUser.objects.filter(trees__type="TON").distinct().count()
        ) or 0

        if active_dist and participants_count > 0:
            total_per_user = (active_dist.total_amount / Decimal(participants_count))
            ton_per_hour = (total_per_user / Decimal(active_dist.duration_hours))
            # Сколько получит пользователь за 5 часов (период полива)
            ton_for_5h = (ton_per_hour * Decimal(5))
        else:
            ton_per_hour = None
            ton_for_5h = None

        context.update({
            "active_distribution": active_dist,
            "participants_count": participants_count,
            "ton_per_hour": ton_per_hour,
            "ton_for_5h": ton_for_5h,
        })

    return render(request, "tree/detail.html", context)


def water_tree(request, tree_id):
    """
    AJAX-обработчик: полив CF- или TON-дерева.
    Должен возвращать JSON с ключами:
      - branch_dropped: True/False
      - amount_cf (если CF-дерево)
      - amount_ton (если TON-дерево и есть активная раздача TON)
    """
    user = get_current_user(request)
    if not user:
        return JsonResponse({"status": "error", "message": "Сначала авторизуйтесь"}, status=403)

    tree = get_object_or_404(Tree, id=tree_id, user=user)

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Требуется метод POST"}, status=400)

    # Предполагается, что ваш метод Tree.water() возвращает словарь вида:
    # {"branch_dropped": bool, "amount_cf": Decimal, "amount_ton": Decimal}
    result = tree.water()

    response_data = {
        "status": "success",
        "message": "Дерево успешно полито",
        "is_watered": True,
        "branch_dropped": result.get("branch_dropped", False),
        "branches_collected": tree.branches_collected,
    }

    if result.get("amount_cf") and result["amount_cf"] > 0:
        response_data["amount_cf"] = float(result["amount_cf"])
        response_data["message"] += f" +{float(result['amount_cf']):.2f} CF"

    if result.get("amount_ton") and result["amount_ton"] > 0:
        response_data["amount_ton"] = float(result["amount_ton"])
        response_data["message"] += f" +{float(result['amount_ton']):.8f} TON"

    return JsonResponse(response_data)


def upgrade_tree(request, tree_id):
    """
    AJAX-обработчик: повышение уровня дерева (использует ветки).
    """
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
        "new_income": float(tree.income_per_hour)
    })
