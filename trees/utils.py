# trees/utils.py

from decimal import Decimal
from django.utils import timezone

from shop.models import Purchase
from .models import Tree

def update_user_balance(user):
    now = timezone.now()
    trees = Tree.objects.filter(user=user, type='CF')
    total_cf = Decimal('0')
    for tree in trees:
        if not tree.last_watered:
            continue
        time_delta = now - tree.last_watered
        hours_passed = min(time_delta.total_seconds() / 3600, tree.WATER_DURATION)
        income = (tree.income_per_hour * Decimal(hours_passed)).quantize(Decimal('0.0000'))
        if income > 0:
            total_cf += income
            tree.last_watered = now
            tree.save(update_fields=["last_watered"])
    if total_cf > 0:
        user.cf_balance += total_cf
        user.save(update_fields=["cf_balance"])


def apply_item_to_tree(user, item_type):
    # 1. Найти CF-дерево пользователя
    cf_tree = Tree.objects.get(user=user, type='CF')

    # 2. Найти первую подходящую покупку предмета
    purchase = Purchase.objects.filter(
        user=user,
        item__type=item_type,
    ).order_by('created_at').first()
    if not purchase:
        return False, "Нет подходящего предмета"

    # 3. Применить эффект (пример для удобрения/полива)
    if item_type == 'fertilizer':
        cf_tree.growth_points += 10  # пример: добавить очки роста
    elif item_type == 'auto_water':
        cf_tree.auto_water_until = timezone.now() + timezone.timedelta(hours=purchase.item.duration or 12)
    # добавь любые другие эффекты

    cf_tree.save()

    # 4. Отметить использование (например, удалить покупку)
    purchase.delete()
    return True, "Предмет успешно применён"

def use_purchase_for_cf_tree(user, purchase_id):
    try:
        purchase = Purchase.objects.get(id=purchase_id, user=user)
        item = purchase.item
    except Purchase.DoesNotExist:
        return False, "Покупка не найдена"

    # Только для CF-дерева
    try:
        tree = Tree.objects.get(user=user, type='CF')
    except Tree.DoesNotExist:
        return False, "CF-дерево не найдено"

    # Применяем предмет
    result = tree.apply_shop_item(item)


    purchase.delete()
    return True, result