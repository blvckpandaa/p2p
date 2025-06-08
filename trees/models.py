from django.db import models
from django.conf import settings
from django.utils import timezone
import random

class Tree(models.Model):
    """Модель дерева в игре"""
    TYPE_CHOICES = [
        ('CF', 'CF Tree'),
        ('TON', 'TON Tree'),

    ]
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='trees')
    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    level = models.IntegerField(default=1)
    income_per_hour = models.FloatField(default=1.0)
    branches_collected = models.IntegerField(default=0)
    last_watered = models.DateTimeField(null=True, blank=True)
    fertilized_until = models.DateTimeField(null=True, blank=True)  # Время действия удобрения
    auto_water_until = models.DateTimeField(null=True, blank=True)  # Время действия автополива
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Дерево'
        verbose_name_plural = 'Деревья'
        unique_together = ['user', 'type']  # У пользователя может быть только одно дерево каждого типа
    
    def __str__(self):
        return f"{self.get_type_display()} (Level {self.level}) - {self.user}"
    
    def is_watered(self):
        """Проверяет, полито ли дерево"""
        if not self.last_watered:
            return False
        
        watering_duration = settings.GAME_SETTINGS.get('WATERING_DURATION', 5)
        watering_expires = self.last_watered + timezone.timedelta(hours=watering_duration)
        
        return timezone.now() < watering_expires
    
    def is_fertilized(self):
        """Проверяет, удобрено ли дерево"""
        if not self.fertilized_until:
            return False
        return timezone.now() < self.fertilized_until
        
    def is_auto_watered(self):
        """Проверяет, активен ли автополив"""
        if not self.auto_water_until:
            return False
        return timezone.now() < self.auto_water_until
    
    def get_current_income(self):
        """Возвращает текущий доход дерева с учетом удобрений"""
        base_income = self.income_per_hour
        
        # Если есть удобрение, доход удваивается
        if self.is_fertilized():
            base_income *= 2
            
        return base_income
    
    def can_upgrade(self):
        """Проверяет, можно ли улучшить дерево"""
        if self.level >= 5:  # Максимальный уровень
            return False
            
        tree_levels = settings.GAME_SETTINGS.get('TREE_LEVELS', {})
        required_branches = tree_levels.get(self.level + 1, {}).get('branches', 0)
        
        return self.branches_collected >= required_branches
    
    def upgrade(self):
        """Улучшает дерево на следующий уровень"""
        if not self.can_upgrade():
            return False
            
        self.level += 1
        tree_levels = settings.GAME_SETTINGS.get('TREE_LEVELS', {})
        self.income_per_hour = tree_levels.get(self.level, {}).get('income', self.income_per_hour)
        self.save()
        
        return True
    
    def water(self):
        """Поливает дерево"""
        # Проверяем, активен ли автополив
        is_auto = self.is_auto_watered()
        
        self.last_watered = timezone.now()
        self.save()
        
        # С вероятностью 10% выпадает ветка (только если уровень < 5)
        # Если автополив активен, увеличиваем шанс выпадения ветки
        if self.level < 5:
            branch_drop_chance = settings.GAME_SETTINGS.get('BRANCH_DROP_CHANCE', 0.1)
            if is_auto:
                branch_drop_chance *= 1.5  # Увеличиваем шанс на 50% при автополиве
                
            if random.random() < branch_drop_chance:
                self.branches_collected += 1
                self.save()
                return True  # Ветка выпала
                
        return False  # Ветка не выпала
    
    def fertilize(self, hours=24):
        """Применяет удобрение к дереву"""
        self.fertilized_until = timezone.now() + timezone.timedelta(hours=hours)
        self.save()
        return True
