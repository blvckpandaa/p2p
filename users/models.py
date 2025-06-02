from django.db import models
import random
import string

def generate_referral_code():
    """Генерирует уникальный реферальный код"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))

class User(models.Model):
    """Модель пользователя, основанная на данных Telegram"""
    telegram_id = models.BigIntegerField(primary_key=True)
    username = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    photo_url = models.URLField(null=True, blank=True)
    
    # Балансы токенов
    cf_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ton_balance = models.DecimalField(max_digits=15, decimal_places=8, default=0)

    # Реферальная система
    referral_code = models.CharField(max_length=20, unique=True, default=generate_referral_code)
    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')
    
    # Даты и статусы
    date_joined = models.DateTimeField(auto_now_add=True)
    last_watered = models.DateTimeField(null=True, blank=True)
    auto_water_until = models.DateTimeField(null=True, blank=True)
    
    # Стейкинг
    staking_cf = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    staking_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        if self.username:
            return f"@{self.username}"
        return f"{self.first_name} {self.last_name or ''}"
    
    def get_full_name(self):
        """Возвращает полное имя пользователя"""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    def is_auto_water_active(self):
        """Проверяет, активен ли авто-полив"""
        from django.utils import timezone
        if not self.auto_water_until:
            return False
        return self.auto_water_until > timezone.now()
    
    def total_referrals(self):
        """Возвращает общее количество рефералов"""
        return self.referrals.count()
    
    def can_access_staking(self):
        """Проверяет, может ли пользователь использовать стейкинг"""
        from django.conf import settings
        min_cf = settings.GAME_SETTINGS.get('MIN_CF_FOR_STAKING', 300)
        return self.cf_balance >= min_cf
    
    def can_access_p2p(self):
        """Проверяет, имеет ли пользователь доступ к P2P-бирже"""
        # Доступ открывается после стейкинга
        return self.staking_until is not None
