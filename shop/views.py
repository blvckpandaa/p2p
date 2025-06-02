from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST

from trees.models import Tree
from trees.views import get_current_user
from .models import ShopItem, Purchase
from django.utils import timezone

def shop(request):
    """Страница магазина"""
    # Получаем все доступные товары
    items = ShopItem.objects.filter(is_active=True)
    user = get_current_user(request)
    ton_tree = Tree.objects.filter(user=user, type='TON').first()


    return render(request, 'shop/index.html', {
        'items': items,
        'user': user,
        'ton_tree': ton_tree,
        'user_has_ton_tree': bool(ton_tree),
    })

@require_POST
def buy_auto_water(request):
    user = get_current_user(request)
    tree_id = request.POST.get("tree_id")
    days = int(request.POST.get("days", 1))  # 1 или 2 суток
    ton_price = 1 if days == 1 else 2
    tree = get_object_or_404(Tree, id=tree_id, user=user)

    if user.ton_balance < ton_price:
        return JsonResponse({"status": "error", "message": "Недостаточно TON"}, status=400)
    # Включаем автополив
    tree.auto_water_enabled = True
    tree.auto_water_until = timezone.now() + timezone.timedelta(days=days)
    tree.save(update_fields=["auto_water_enabled", "auto_water_until"])
    user.ton_balance -= ton_price
    user.save(update_fields=["ton_balance"])
    return JsonResponse({"status": "success", "message": "Автополив активирован!"})

@require_POST
def buy_fertilizer(request):
    user = get_current_user(request)
    tree_id = request.POST.get("tree_id")
    ton_price = 1
    tree = get_object_or_404(Tree, id=tree_id, user=user)
    if user.ton_balance < ton_price:
        return JsonResponse({"status": "error", "message": "Недостаточно TON"}, status=400)
    # Включаем удобрение на 24ч
    tree.fertilized_until = timezone.now() + timezone.timedelta(hours=24)
    tree.save(update_fields=["fertilized_until"])
    user.ton_balance -= ton_price
    user.save(update_fields=["ton_balance"])
    return JsonResponse({"status": "success", "message": "Удобрение куплено!"})

@require_POST
def buy_branches(request):
    user = get_current_user(request)
    tree_id = request.POST.get("tree_id")
    qty = int(request.POST.get("quantity", 1))
    ton_price = qty  # 1 ветка = 1 TON
    tree = get_object_or_404(Tree, id=tree_id, user=user)
    if user.ton_balance < ton_price:
        return JsonResponse({"status": "error", "message": "Недостаточно TON"}, status=400)
    tree.branches_collected += qty
    tree.save(update_fields=["branches_collected"])
    user.ton_balance -= ton_price
    user.save(update_fields=["ton_balance"])
    return JsonResponse({"status": "success", "message": f"Куплено веток: {qty}"})

def buy_ton_tree(request):
    user = get_current_user(request)
    if not user:
        return redirect("telegram_login")

    # Проверка, что у пользователя ещё нет TON-дерева
    if Tree.objects.filter(user=user, type='TON').exists():
        messages.warning(request, "У вас уже есть TON-дерево.")
        return redirect("home")

    cost_ton = 1  # допустим, 1 TON
    if user.ton_balance < cost_ton:
        messages.error(request, "Недостаточно TON для покупки TON-дерева.")
        return redirect("home")

    # Списываем TON и создаём дерево
    user.ton_balance -= cost_ton
    user.save(update_fields=["ton_balance"])
    Tree.objects.create(user=user, type="TON")

    messages.success(request, "TON-дерево успешно куплено!")
    return redirect("home")
