# trees/views.py

from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Tree, TonDistribution
from users.models import User as TelegramUser, User


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
    user = get_current_user(request)
    if not user:
        return render(request, "not_authenticated.html")

    cf_trees = Tree.objects.filter(user=user, type="CF")
    if not cf_trees.exists():
        Tree.objects.create(user=user, type="CF")
        cf_trees = Tree.objects.filter(user=user, type="CF")

    ton_trees = Tree.objects.filter(user=user, type="TON")

    active_distribution = TonDistribution.objects.filter(is_active=True).last()
    participants_count = (
        TelegramUser.objects.filter(trees__type="TON").distinct().count()
    ) or 0

    ton_per_hour_per_user = None
    if active_distribution and participants_count > 0:
        total_per_user = (active_distribution.total_amount / Decimal(participants_count))
        ton_per_hour_per_user = (total_per_user / Decimal(active_distribution.duration_hours))

    # Собираем нужные значения для каждого CF-дерева
    cf_tree_infos = []
    for tree in cf_trees:
        cf_tree_infos.append({
            "id": tree.id,
            "level": tree.level,
            "income_per_hour": float(tree.income_per_hour),
            "branches_collected": tree.branches_collected,
            "last_watered": tree.last_watered,
            "water_percent": tree.get_water_percent(),
            "pending_income": float(tree.get_pending_income()),
            "is_watered": tree.is_watered(),
        })

    # Аналогично можешь добавить для TON, если хочешь отображать процент и доход
    # ton_tree_infos = [...]

    return render(request, "home.html", {
        "user": user,
        "cf_trees": cf_tree_infos,
        # "ton_trees": ton_tree_infos, # если сделаешь аналогично
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
    TOTAL_CREATED_CF = 25_000_000
    all_cf_grown = User.objects.aggregate(total=Sum('cf_balance'))['total'] or 0

    user_cf_grown = user.cf_balance if user else 0


    # Базовый контекст
    context = {
        "user": user,
        "tree": tree,
        "is_watered": is_watered,
        "is_fertilized": is_fertilized,
        "can_upgrade": can_upgrade,
        "water_percent": tree.get_water_percent(),  # <--- новый %
        "pending_income": float(tree.get_pending_income()),
        'total_created_cf': TOTAL_CREATED_CF,
        'all_cf_grown': all_cf_grown,
        "user_cf_grown": user_cf_grown,
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
    user = get_current_user(request)
    if not user:
        return JsonResponse({"status": "error", "message": "Сначала авторизуйтесь"}, status=403)

    tree = get_object_or_404(Tree, id=tree_id, user=user)

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Требуется метод POST"}, status=400)

    result = tree.water()

    response_data = {
        "status": "success",
        "message": "Дерево успешно полито",
        "is_watered": True,
        "branch_dropped": result.get("branch_dropped", False),
        "branches_collected": tree.branches_collected,
        "amount_cf": float(result.get("amount_cf", 0)),
        "amount_ton": float(result.get("amount_ton", 0)),
        # Новые поля для обновления на фронте:
        "water_percent": tree.get_water_percent(),
        "pending_income": float(tree.get_pending_income()),
    }
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


@csrf_exempt  # или используй @login_required
def collect_income(request, tree_id):
    user = get_current_user(request)
    if not user:
        return JsonResponse({"status": "error", "message": "Сначала авторизуйтесь"}, status=403)
    tree = get_object_or_404(Tree, id=tree_id, user=user)
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Требуется POST"}, status=400)

    # Логика: считаем накопленный доход и зачисляем на баланс
    now = timezone.now()
    if tree.last_watered:
        seconds_since = (now - tree.last_watered).total_seconds()
        hours = min(seconds_since / 3600, 5)
    else:
        hours = 0

    if hours <= 0:
        return JsonResponse({"status": "error", "message": "Нет накопленного дохода"}, status=400)

    # CF-дерево
    if tree.type == 'CF':
        pending = (tree.income_per_hour * Decimal(hours)).quantize(Decimal('0.0000'))
        user.cf_balance += pending
        user.save(update_fields=["cf_balance"])
    # TON-дерево (если хочешь реализовать)
    elif tree.type == 'TON':
        # ... логику TON смотри по своему проекту
        pending = Decimal('0')  # ТУТ добавь свою формулу

    # Обнуляем last_watered чтобы нельзя было собрать повторно
    tree.last_watered = now
    tree.save(update_fields=["last_watered"])

    return JsonResponse({
        "status": "success",
        "collected": float(pending),
        "new_balance_cf": float(user.cf_balance),
    })