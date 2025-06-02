from django.db import models
from django.utils import timezone
from django.conf import settings

class Order(models.Model):
    """Модель ордера на P2P-бирже"""
    TYPE_CHOICES = [
        ('buy', 'Покупка'),
        ('sell', 'Продажа'),
    ]
    
    TOKEN_CHOICES = [
        ('CF', 'CF Token'),
        ('TON', 'TON Token'),
        ('NOT', 'NOT Token'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Активный'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
        ('expired', 'Истек'),
    ]
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='orders', verbose_name='Пользователь')
    type = models.CharField(max_length=4, choices=TYPE_CHOICES, verbose_name='Тип')
    token_type = models.CharField(max_length=3, choices=TOKEN_CHOICES, verbose_name='Тип токена')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Количество')
    price_per_unit = models.DecimalField(max_digits=15, decimal_places=8, verbose_name='Цена за единицу')
    min_amount = models.DecimalField(max_digits=15, decimal_places=2, default=100, verbose_name='Минимальная сумма')
    payment_details = models.TextField(verbose_name='Платежные реквизиты', blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    expires_at = models.DateTimeField(verbose_name='Истекает')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')
    
    class Meta:
        verbose_name = 'Ордер'
        verbose_name_plural = 'Ордера'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_type_display()} {self.amount} {self.token_type} @ {self.price_per_unit} ({self.user})"
    
    def save(self, *args, **kwargs):
        # Если это новый ордер, устанавливаем дату истечения
        if not self.pk and not self.expires_at:
            days = settings.GAME_SETTINGS.get('ORDER_EXPIRY', 3)
            self.expires_at = timezone.now() + timezone.timedelta(days=days)
        super().save(*args, **kwargs)
    
    def total_price(self):
        """Возвращает общую стоимость ордера"""
        return self.amount * self.price_per_unit
    
    def mark_as_completed(self):
        """Отмечает ордер как завершенный"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def mark_as_expired(self):
        """Отмечает ордер как истекший"""
        self.status = 'expired'
        self.save()
    
    def is_expired(self):
        """Проверяет, истек ли ордер"""
        return timezone.now() > self.expires_at
    
    def is_active(self):
        """Проверяет, активен ли ордер"""
        return self.status == 'active' and not self.is_expired()

class Transaction(models.Model):
    """Модель транзакции на P2P-бирже"""
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions', verbose_name='Ордер')
    buyer = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='p2p_purchases', verbose_name='Покупатель')
    seller = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='p2p_sales', verbose_name='Продавец')
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Количество')
    price_per_unit = models.DecimalField(max_digits=15, decimal_places=8, verbose_name='Цена за единицу')
    token_type = models.CharField(max_length=3, choices=Order.TOKEN_CHOICES, verbose_name='Тип токена')
    commission = models.DecimalField(max_digits=15, decimal_places=8, verbose_name='Комиссия')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.buyer} купил {self.amount} {self.token_type} у {self.seller}"
    
    def total_amount(self):
        """Возвращает общую сумму транзакции"""
        return self.amount * self.price_per_unit

class Message(models.Model):
    """Модель сообщений между участниками сделки"""
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='messages', verbose_name='Сделка')
    sender = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Отправитель')
    content = models.TextField(verbose_name='Содержание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата отправки')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    
    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Сообщение от {self.sender} в сделке {self.transaction.id}"
