from django.db import models
from django.utils import timezone

class ShopItem(models.Model):
    """Модель товара в магазине"""
    TYPE_CHOICES = [
        ('auto_water', 'Авто-полив'),
        ('fertilizer', 'Удобрение'),
        ('ton_tree', 'Дерево TON'),
        ('cf_slot', 'CF Слот'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='Название')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Тип')
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    price_token_type = models.CharField(max_length=3, default='CF', verbose_name='Тип токена для оплаты')
    duration = models.IntegerField(help_text='Длительность в часах', null=True, blank=True, verbose_name='Длительность')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    image = models.CharField(max_length=255, blank=True, help_text='URL изображения или иконки', verbose_name='Изображение')
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
    
    def __str__(self):
        if self.duration:
            return f"{self.name} ({self.duration} ч.)"
        return self.name

class Purchase(models.Model):
    """Модель покупки в магазине"""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='purchases', verbose_name='Пользователь')
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE, related_name='purchases', verbose_name='Товар')
    price_paid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Оплаченная цена')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата покупки')
    valid_until = models.DateTimeField(null=True, blank=True, verbose_name='Действует до')
    
    class Meta:
        verbose_name = 'Покупка'
        verbose_name_plural = 'Покупки'
    
    def __str__(self):
        return f"{self.user} - {self.item} ({self.created_at.strftime('%d.%m.%Y')})"
    
    def is_active(self):
        """Проверяет, активна ли покупка"""
        if not self.valid_until:
            return True  # Бессрочная покупка
        return timezone.now() < self.valid_until
