from django.db import models

class Notification(models.Model):
    """Модель уведомления"""
    TYPE_CHOICES = [
        ('watering', 'Полив'),
        ('auto_water', 'Авто-полив'),
        ('order', 'Ордер'),
        ('staking', 'Стейкинг'),
        ('referral', 'Реферал'),
        ('system', 'Системное'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает отправки'),
        ('sent', 'Отправлено'),
        ('read', 'Прочитано'),
        ('failed', 'Ошибка'),
    ]
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications', verbose_name='Пользователь')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name='Тип')
    title = models.CharField(max_length=100, verbose_name='Заголовок')
    message = models.TextField(verbose_name='Сообщение')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата отправки')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата прочтения')
    
    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_type_display()} для {self.user}: {self.title}"
    
class NotificationSettings(models.Model):
    """Настройки уведомлений пользователя"""
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='notification_settings', verbose_name='Пользователь')
    watering_notifications = models.BooleanField(default=True, verbose_name='Уведомления о поливе')
    auto_water_notifications = models.BooleanField(default=True, verbose_name='Уведомления об авто-поливе')
    order_notifications = models.BooleanField(default=True, verbose_name='Уведомления об ордерах')
    staking_notifications = models.BooleanField(default=True, verbose_name='Уведомления о стейкинге')
    referral_notifications = models.BooleanField(default=True, verbose_name='Уведомления о рефералах')
    system_notifications = models.BooleanField(default=True, verbose_name='Системные уведомления')
    
    # Настройки каналов уведомлений
    telegram_notifications = models.BooleanField(default=True, verbose_name='Уведомления через Telegram')
    email_notifications = models.BooleanField(default=False, verbose_name='Уведомления по Email')
    email = models.EmailField(null=True, blank=True, verbose_name='Email для уведомлений')
    
    class Meta:
        verbose_name = 'Настройки уведомлений'
        verbose_name_plural = 'Настройки уведомлений'
    
    def __str__(self):
        return f"Настройки уведомлений для {self.user}"
