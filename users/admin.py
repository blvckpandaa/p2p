from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Count, F, Q
from datetime import timedelta

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели User
    """
    list_display = ('telegram_id', 'username_display', 'full_name', 'tokens_balances', 
                   'staking_status', 'referrals_count', 'trees_count', 
                   'date_joined', 'last_activity', 'online_status')
    list_filter = ('date_joined', 'staking_until', 'auto_water_until')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name')
    readonly_fields = ('date_joined', 'referred_by_link', 'last_watered', 'auto_water_until', 
                       'staking_until', 'referral_code', 'telegram_link', 'user_avatar')
    list_per_page = 20
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('telegram_id', 'username', 'first_name', 'last_name', 'photo_url', 'user_avatar')
        }),
        ('Телеграм', {
            'fields': ('telegram_link',)
        }),
        ('Балансы', {
            'fields': ('cf_balance', 'ton_balance')
        }),
        ('Реферальная система', {
            'fields': ('referral_code', 'referred_by', 'referred_by_link')
        }),
        ('Статусы и даты', {
            'fields': ('date_joined', 'last_watered', 'auto_water_until')
        }),
        ('Стейкинг', {
            'fields': ('staking_cf', 'staking_until')
        }),
    )
    
    actions = ['give_cf_tokens', 'give_ton_tokens',
              'extend_auto_water', 'extend_staking']
    
    def username_display(self, obj):
        """Отображение имени пользователя"""
        if obj.username:
            username = f"@{obj.username}"
            return format_html('<span style="color: #3a1a78; font-weight: bold;">{}</span>', username)
        return "-"
    
    username_display.short_description = 'Никнейм'
    username_display.admin_order_field = 'username'
    
    def full_name(self, obj):
        """Полное имя пользователя"""
        return obj.get_full_name()

    full_name.short_description = 'Имя'

    def tokens_balances(self, obj):
        """
        Отображение балансов токенов CF и TON в админке.
        Здесь мы сразу форматируем числа в строки, чтобы в format_html уже не было числовых спецификаторов.
        """
        cf_color = "#f9ca24"  # Желтый
        ton_color = "#0f7fd8"  # Синий

        # Безопасно приводим Decimal (или None) к float
        try:
            cf_val = float(obj.cf_balance)
        except Exception:
            cf_val = 0.0

        try:
            ton_val = float(obj.ton_balance)
        except Exception:
            ton_val = 0.0

        # Сразу формируем строку вида "12.34" и "0.01234567"
        cf_str = f"{cf_val:.2f}"
        ton_str = f"{ton_val:.8f}"

        return format_html(
            '<div style="display: flex; gap: 10px;">'
            '  <div>'
            '    <span style="color: {}; font-weight: bold;">{} CF</span>'
            '  </div>'
            '  <div>'
            '    <span style="color: {}; font-weight: bold;">{} TON</span>'
            '  </div>'
            '</div>',
            cf_color, cf_str,
            ton_color, ton_str
        )

    tokens_balances.short_description = 'Балансы'

    def staking_status(self, obj):
        """Статус стейкинга"""
        if not obj.staking_until:
            return format_html('<span style="color: #dc3545;">Не активен</span>')
        
        if obj.staking_until > timezone.now():
            days_left = (obj.staking_until - timezone.now()).days
            return format_html(
                '<span style="color: #28a745;">Активен</span> '
                '<small>({} CF, {} дн.)</small>',
                obj.staking_cf, days_left
            )
        return format_html('<span style="color: #ffc107;">Истек</span>')
    
    staking_status.short_description = 'Стейкинг'
    
    def referrals_count(self, obj):
        """Количество рефералов"""
        count = obj.total_referrals()
        url = reverse('admin:users_user_changelist') + f'?referred_by__telegram_id__exact={obj.telegram_id}'
        
        return format_html('<a href="{}" style="color: #0f7fd8; font-weight: bold;">{}</a>', url, count)
    
    referrals_count.short_description = 'Рефералы'
    
    def trees_count(self, obj):
        """Количество деревьев пользователя"""
        count = obj.trees.count()
        url = reverse('admin:trees_tree_changelist') + f'?user__telegram_id__exact={obj.telegram_id}'
        
        if count > 0:
            return format_html('<a href="{}" style="color: #28a745; font-weight: bold;">{}</a>', url, count)
        return format_html('<span style="color: #dc3545;">0</span>')
    
    trees_count.short_description = 'Деревья'
    
    def last_activity(self, obj):
        """Последняя активность пользователя"""
        activities = []
        
        if obj.last_watered:
            activities.append(('Полив', obj.last_watered, '#28a745'))
        
        # Получаем последнюю транзакцию P2P
        try:
            last_transaction = obj.transactions_as_buyer.first() or obj.transactions_as_seller.first()
            if last_transaction:
                activities.append(('P2P', last_transaction.created_at, '#0f7fd8'))
        except:
            pass
        
        # Получаем последнюю покупку
        try:
            last_purchase = obj.purchases.first()
            if last_purchase:
                activities.append(('Покупка', last_purchase.created_at, '#f9ca24'))
        except:
            pass
        
        if not activities:
            return '-'
        
        # Сортируем по дате (самые новые вверху)
        activities.sort(key=lambda x: x[1], reverse=True)
        latest = activities[0]
        
        return format_html(
            '<span style="color: {};">{}: {}</span>',
            latest[2], latest[0], latest[1].strftime('%d.%m.%Y %H:%M')
        )
    
    last_activity.short_description = 'Последняя активность'
    
    def online_status(self, obj):
        """Статус онлайн пользователя"""
        # Проверяем активность за последние 15 минут
        if obj.last_watered and obj.last_watered > timezone.now() - timedelta(minutes=15):
            return format_html('<span style="color: #28a745;"><i class="fas fa-circle"></i> Online</span>')
        return format_html('<span style="color: #dc3545;"><i class="fas fa-circle"></i> Offline</span>')
    
    online_status.short_description = 'Статус'
    
    def referred_by_link(self, obj):
        """Ссылка на пригласившего пользователя"""
        if not obj.referred_by:
            return '-'
        
        url = reverse('admin:users_user_change', args=[obj.referred_by.telegram_id])
        return format_html('<a href="{}">{} ({})</a>', 
                         url, obj.referred_by, obj.referred_by.telegram_id)
    
    referred_by_link.short_description = 'Приглашен пользователем'
    
    def telegram_link(self, obj):
        """Ссылка на Telegram профиль"""
        if obj.username:
            return format_html('<a href="https://t.me/{}" target="_blank" rel="noopener">@{}</a>', 
                            obj.username, obj.username)
        return format_html('<a href="https://t.me/user?id={}" target="_blank" rel="noopener">Профиль</a>', 
                         obj.telegram_id)
    
    telegram_link.short_description = 'Ссылка на Telegram'
    
    def user_avatar(self, obj):
        """Аватар пользователя"""
        if obj.photo_url:
            return format_html('<img src="{}" width="100" height="100" style="border-radius: 50%;" />', 
                             obj.photo_url)
        return '-'
    
    user_avatar.short_description = 'Аватар'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).prefetch_related('trees', 'referrals')
    
    def give_cf_tokens(self, request, queryset):
        """Выдача CF токенов"""
        from django.contrib.admin.helpers import ActionForm
        from django import forms
        
        class CfAmountForm(ActionForm):
            amount = forms.DecimalField(label='Количество CF')
        
        self.action_form = CfAmountForm
        amount = request.POST.get('amount')
        
        if 'apply' in request.POST and amount:
            amount = float(amount)
            updated = 0
            
            for user in queryset:
                user.cf_balance += amount
                user.save()
                updated += 1
            
            self.message_user(request, f'Выдано {amount} CF токенов {updated} пользователям.')
    
    give_cf_tokens.short_description = "Выдать CF токены"
    
    def give_ton_tokens(self, request, queryset):
        """Выдача TON токенов"""
        from django.contrib.admin.helpers import ActionForm
        from django import forms
        
        class TonAmountForm(ActionForm):
            amount = forms.DecimalField(label='Количество TON')
        
        self.action_form = TonAmountForm
        amount = request.POST.get('amount')
        
        if 'apply' in request.POST and amount:
            amount = float(amount)
            updated = 0
            
            for user in queryset:
                user.ton_balance += amount
                user.save()
                updated += 1
            
            self.message_user(request, f'Выдано {amount} TON токенов {updated} пользователям.')
    
    give_ton_tokens.short_description = "Выдать TON токены"
    

    
    def extend_auto_water(self, request, queryset):
        """Продление периода авто-полива"""
        from django.contrib.admin.helpers import ActionForm
        from django import forms
        
        class AutoWaterForm(ActionForm):
            days = forms.IntegerField(label='Количество дней')
        
        self.action_form = AutoWaterForm
        days = request.POST.get('days')
        
        if 'apply' in request.POST and days:
            days = int(days)
            updated = 0
            
            for user in queryset:
                if user.auto_water_until and user.auto_water_until > timezone.now():
                    user.auto_water_until = user.auto_water_until + timedelta(days=days)
                else:
                    user.auto_water_until = timezone.now() + timedelta(days=days)
                user.save()
                updated += 1
            
            self.message_user(request, f'Продлен авто-полив на {days} дней для {updated} пользователей.')
    
    extend_auto_water.short_description = "Продлить авто-полив"
    
    def extend_staking(self, request, queryset):
        """Продление периода стейкинга"""
        from django.contrib.admin.helpers import ActionForm
        from django import forms
        
        class StakingForm(ActionForm):
            days = forms.IntegerField(label='Количество дней')
        
        self.action_form = StakingForm
        days = request.POST.get('days')
        
        if 'apply' in request.POST and days:
            days = int(days)
            updated = 0
            
            for user in queryset:
                if user.staking_until and user.staking_until > timezone.now():
                    user.staking_until = user.staking_until + timedelta(days=days)
                else:
                    user.staking_until = timezone.now() + timedelta(days=days)
                user.save()
                updated += 1
            
            self.message_user(request, f'Продлен стейкинг на {days} дней для {updated} пользователей.')
    
    extend_staking.short_description = "Продлить стейкинг"
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }
