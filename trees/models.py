# trees/models.py

import random
from decimal import Decimal
from django.db import models
from django.utils import timezone

from users.models import User as TelegramUser

class Tree(models.Model):
    TYPE_CHOICES = (
        ('CF', 'CryptoFarm'),
        ('TON', 'TON-Дерево'),
    )

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="trees")
    type = models.CharField(max_length=3, choices=TYPE_CHOICES, default='CF')
    level = models.PositiveSmallIntegerField(default=1)
    income_per_hour = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('1.0'))
    branches_collected = models.PositiveIntegerField(default=0)

    last_watered = models.DateTimeField(null=True, blank=True)
    fertilized_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    BRANCH_DROP_CHANCE = 0.10  # 10% шанс получить ветку

    def is_watered(self):
        """Проверяем, не истёк ли период полива (5 часов)."""
        if not self.last_watered:
            return False
        now = timezone.now()
        expiry = self.last_watered + timezone.timedelta(hours=5)
        return now < expiry

    def is_fertilized(self):
        """Проверяем, не истёк ли эффект удобрения."""
        if not self.fertilized_until:
            return False
        return timezone.now() < self.fertilized_until

    def can_upgrade(self):
        """
        Проверяет, хватает ли веток для перехода на следующий уровень.
        Допустим, у вас в settings.GAME_SETTINGS["TREE_LEVELS"] хранится словарь с условием:
          {1: {"branches": 0, "income": 1.0}, 2: {"branches": 5, "income": 1.5}, ...}
        """
        from django.conf import settings
        next_level = self.level + 1
        levels = settings.GAME_SETTINGS.get("TREE_LEVELS", {})
        if next_level not in levels:
            return False
        required_branches = levels[next_level]["branches"]
        return self.branches_collected >= required_branches

    def upgrade(self):
        """
        Повышает уровень дерева (если хватает веток). Списывает нужные ветки и пересчитывает income_per_hour.
        """
        from django.conf import settings
        levels = settings.GAME_SETTINGS.get("TREE_LEVELS", {})
        next_level = self.level + 1
        if next_level not in levels:
            return False

        required_branches = levels[next_level]["branches"]
        if self.branches_collected < required_branches:
            return False

        # Списываем ветки
        self.branches_collected -= required_branches
        # Увеличиваем уровень
        self.level = next_level
        # Пересчитываем доход (берём из GAME_SETTINGS формулу или множитель)
        self.income_per_hour = Decimal(levels[next_level]["income"])
        self.save(update_fields=["level", "branches_collected", "income_per_hour"])
        return True

    def water(self):
        """
        Полив дерева:
          1. Обновляем last_watered = now
          2. Генерируем ветку с вероятностью BRANCH_DROP_CHANCE
          3. Начисляем пользователю:
             - CF: income_per_hour * 5 часов сразу в cf_balance
             - TON: только если есть активная раздача, считаем свою долю
        Возвращает словарь:
          {"branch_dropped": bool, "amount_cf": Decimal, "amount_ton": Decimal}
        """
        now = timezone.now()
        self.last_watered = now
        self.save(update_fields=["last_watered"])

        # Попытка выпадения ветки
        branch_dropped = False
        if random.random() < self.BRANCH_DROP_CHANCE:
            branch_dropped = True
            self.branches_collected += 1
            self.save(update_fields=["branches_collected"])

        amount_cf = Decimal('0')
        amount_ton = Decimal('0')

        # Если CF-дерево — начисляем CF
        if self.type == "CF":
            # Например, пользователь получает income_per_hour * 5 за этот полив
            total_cf = (self.income_per_hour * Decimal(5)).quantize(Decimal('0.0000'))
            user = self.user
            user.cf_balance = user.cf_balance + total_cf
            user.save(update_fields=["cf_balance"])
            amount_cf = total_cf

        # Если TON-дерево — начисляем TON только если есть активная раздача
        elif self.type == "TON":
            from .models import TonDistribution
            active_qs = TonDistribution.objects.filter(is_active=True)
            if active_qs.exists():
                dist = active_qs.last()
                # Сколько участников (сколько людей с TON-деревьями)
                participants_count = TelegramUser.objects.filter(trees__type="TON").distinct().count() or 0
                if participants_count > 0:
                    # Доля пользователя за весь период
                    total_per_user = (dist.total_amount / Decimal(participants_count))
                    # За 1 час
                    ton_per_hour = (total_per_user / Decimal(dist.duration_hours)).quantize(Decimal('0.00000001'))
                    # За 5 часов
                    ton_for_5h = (ton_per_hour * Decimal(5)).quantize(Decimal('0.00000001'))
                    # Начисляем
                    user = self.user
                    user.ton_balance = user.ton_balance + ton_for_5h
                    user.save(update_fields=["ton_balance"])
                    amount_ton = ton_for_5h

        return {
            "branch_dropped": branch_dropped,
            "amount_cf": amount_cf,
            "amount_ton": amount_ton
        }


class TonDistribution(models.Model):
    """
    Модель «раздачи» TON:
      - total_amount: общее количество TON в этой раздаче
      - duration_hours: сколько часов действует
      - is_active: True до тех пор, пока админ не нажмёт «Выполнить раздачу»
      - created_at: дата/время создания
    Метод distribute() должен пометить is_active=False и, возможно, разослать уведомления.
    """
    total_amount = models.DecimalField(max_digits=20, decimal_places=8)
    duration_hours = models.PositiveIntegerField(default=24)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def distribute(self):
        """
        Вызывается из админки, переводит раздачу в is_active=False
        Возвращает: сколько получил каждый пользователь (за весь период)
        """
        if not self.is_active:
            return None
        from users.models import User as TelegramUser
        participants_count = TelegramUser.objects.filter(trees__type="TON").distinct().count() or 0
        if participants_count == 0:
            self.is_active = False
            self.save(update_fields=["is_active"])
            return Decimal('0')
        total_per_user = (self.total_amount / Decimal(participants_count)).quantize(Decimal('0.00000001'))
        self.is_active = False
        self.save(update_fields=["is_active"])
        return total_per_user

    def __str__(self):
        return f"Раздача TON #{self.id} — {self.total_amount} TON ({'активна' if self.is_active else 'завершена'}) - {self.duration_hours}ч"
