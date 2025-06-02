from django.db import models
from django.utils import timezone
from django.conf import settings

class Staking(models.Model):
    """Модель стейкинга токенов"""
    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('completed', 'Завершен'),
        ('claimed', 'Получен'),
    ]
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='stakings', verbose_name='Пользователь')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Сумма')
    token_type = models.CharField(max_length=3, default='CF', verbose_name='Тип токена')
    reward_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='Сумма вознаграждения')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    start_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата начала')
    end_date = models.DateTimeField(verbose_name='Дата окончания')
    claimed_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата получения')
    
    class Meta:
        verbose_name = 'Стейкинг'
        verbose_name_plural = 'Стейкинги'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.user} - {self.amount} {self.token_type} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Если это новый стейкинг, рассчитываем дату окончания и награду
        if not self.pk and not self.end_date:
            staking_days = settings.GAME_SETTINGS.get('STAKING_DURATION', 7)
            self.end_date = timezone.now() + timezone.timedelta(days=staking_days)
            
            # Рассчитываем награду
            staking_bonus = settings.GAME_SETTINGS.get('STAKING_BONUS', 0.1)
            self.reward_amount = self.amount * staking_bonus
            
        super().save(*args, **kwargs)
    
    def is_completed(self):
        """Проверяет, завершен ли стейкинг по времени"""
        return timezone.now() >= self.end_date
    
    def complete(self):
        """Отмечает стейкинг как завершенный"""
        if self.status == 'active' and self.is_completed():
            self.status = 'completed'
            self.save()
            return True
        return False
    
    def claim_reward(self):
        """Позволяет пользователю получить награду за стейкинг"""
        if self.status == 'completed':
            self.status = 'claimed'
            self.claimed_date = timezone.now()
            self.save()
            
            # Обновляем баланс пользователя
            user = self.user
            if self.token_type == 'CF':
                user.cf_balance += (self.amount + self.reward_amount)
                user.save()
            
            return True
        return False
