# trees/utils.py

from decimal import Decimal
from django.utils import timezone
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
