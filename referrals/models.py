from django.db import models

# Create your models here.

class Referral(models.Model):
    """Модель реферальной связи"""
    inviter = models.ForeignKey('users.User', related_name='invited_users', on_delete=models.CASCADE, verbose_name='Пригласивший')
    invited = models.ForeignKey('users.User', related_name='invited_by', on_delete=models.CASCADE, verbose_name='Приглашенный')
    bonus_cf = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Бонус CF')
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')
    
    class Meta:
        verbose_name = 'Реферал'
        verbose_name_plural = 'Рефералы'
        unique_together = ['inviter', 'invited']  # Предотвращает дублирование реферальных связей
    
    def __str__(self):
        return f"{self.inviter} пригласил {self.invited}"

class ReferralBonus(models.Model):
    """Модель бонуса от реферала"""
    BONUS_TYPE_CHOICES = [
        ('signup', 'Регистрация'),
        ('income', 'Доход с дерева'),
        ('purchase', 'Покупка'),
    ]
    
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='bonuses', verbose_name='Реферал')
    bonus_type = models.CharField(max_length=10, choices=BONUS_TYPE_CHOICES, verbose_name='Тип бонуса')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    description = models.CharField(max_length=255, blank=True, verbose_name='Описание')
    
    class Meta:
        verbose_name = 'Реферальный бонус'
        verbose_name_plural = 'Реферальные бонусы'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.referral.inviter} получил {self.amount} CF от {self.referral.invited} ({self.get_bonus_type_display()})"
