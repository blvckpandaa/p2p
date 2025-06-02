from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Count, F, Q
from datetime import timedelta

from .models import Referral


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели Referral
    """
    list_display = ('id', 'inviter_link', 'invited_link', 'referral_arrow', 'bonus_display', 
                   'date_joined', 'days_active')
    list_filter = ('date_joined',)
    search_fields = ('inviter__username', 'inviter__telegram_id', 
                    'invited__username', 'invited__telegram_id')
    readonly_fields = ('date_joined', 'inviter_stats', 'invited_stats')
    list_per_page = 25
    date_hierarchy = 'date_joined'
    
    fieldsets = (
        ('Информация о реферальной связи', {
            'fields': ('inviter', 'invited', 'bonus_cf', 'date_joined')
        }),
        ('Статистика приглашающего', {
            'fields': ('inviter_stats',)
        }),
        ('Статистика приглашенного', {
            'fields': ('invited_stats',)
        }),
    )
    
    actions = ['give_bonus_to_inviters', 'recalculate_bonuses']
    
    def inviter_link(self, obj):
        """Ссылка на приглашающего"""
        url = reverse("admin:users_user_change", args=[obj.inviter.telegram_id])
        return format_html('<a href="{}" style="color: #28a745; font-weight: bold;">'
                         '<i class="fas fa-user-plus"></i> {}</a>', 
                         url, obj.inviter)
    
    inviter_link.short_description = 'Приглашающий'
    inviter_link.admin_order_field = 'inviter__username'
    
    def invited_link(self, obj):
        """Ссылка на приглашенного"""
        url = reverse("admin:users_user_change", args=[obj.invited.telegram_id])
        return format_html('<a href="{}" style="color: #0f7fd8; font-weight: bold;">'
                         '<i class="fas fa-user"></i> {}</a>', 
                         url, obj.invited)
    
    invited_link.short_description = 'Приглашенный'
    invited_link.admin_order_field = 'invited__username'
    
    def referral_arrow(self, obj):
        """Стрелка между пользователями"""
        return format_html('<span style="color: #f9ca24; font-size: 18px;">'
                         '<i class="fas fa-long-arrow-alt-right"></i></span>')
    
    referral_arrow.short_description = ''
    
    def bonus_display(self, obj):
        """Отображение бонуса"""
        if obj.bonus_cf:
            return format_html('<span style="color: #f9ca24; font-weight: bold;">'
                             '+{} CF</span>', obj.bonus_cf)
        return format_html('<span style="color: #6c757d;">Нет бонуса</span>')
    
    bonus_display.short_description = 'Бонус'
    bonus_display.admin_order_field = 'bonus_cf'
    
    def days_active(self, obj):
        """Количество дней активности"""
        days = (timezone.now() - obj.date_joined).days
        
        if days < 1:
            hours = int((timezone.now() - obj.date_joined).total_seconds() / 3600)
            return format_html('<span style="color: #17a2b8;">{} часов</span>', hours)
        elif days < 30:
            return format_html('<span style="color: #28a745;">{} дней</span>', days)
        elif days < 180:
            months = days // 30
            return format_html('<span style="color: #0f7fd8;">{} месяцев</span>', months)
        else:
            return format_html('<span style="color: #9c88ff;">{} дней</span>', days)
    
    days_active.short_description = 'Активность'
    
    def inviter_stats(self, obj):
        """Статистика приглашающего пользователя"""
        inviter = obj.inviter
        total_referrals = inviter.invited_users.count()
        
        # Собираем данные о пользователе
        has_cf_tree = inviter.trees.filter(type='CF').exists()
        has_ton_tree = inviter.trees.filter(type='TON').exists()
        has_not_tree = inviter.trees.filter(type='NOT').exists()
        
        # Создаем HTML с информацией
        return format_html(
            '<div style="background-color: #f5f5f5; padding: 15px; border-radius: 10px; margin-top: 10px;">'
            '<h3 style="margin-top: 0; color: #28a745;">Приглашающий: {}</h3>'
            '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">'
            '<div><strong>Telegram ID:</strong> {}</div>'
            '<div><strong>Дата регистрации:</strong> {}</div>'
            '<div><strong>Всего рефералов:</strong> <span style="color: #28a745; font-weight: bold;">{}</span></div>'
            '<div><strong>Реферальный код:</strong> <span style="color: #0f7fd8; font-weight: bold;">{}</span></div>'
            '</div>'
            '<div style="margin-top: 10px;">'
            '<strong>Балансы:</strong> '
            '<span style="color: #f9ca24; font-weight: bold;">{:.2f} CF</span>, '
            '<span style="color: #0f7fd8; font-weight: bold;">{:.8f} TON</span>, '
            '<span style="color: #9c88ff; font-weight: bold;">{:.2f} NOT</span>'
            '</div>'
            '<div style="margin-top: 10px;">'
            '<strong>Деревья:</strong> '
            '{} CF, {} TON, {} NOT'
            '</div>'
            '</div>',
            inviter,
            inviter.telegram_id,
            inviter.date_joined.strftime('%d.%m.%Y'),
            total_referrals,
            inviter.referral_code,
            inviter.cf_balance,
            inviter.ton_balance,
            inviter.not_balance,
            '<span style="color: #28a745;"><i class="fas fa-check"></i></span>' if has_cf_tree else '<span style="color: #dc3545;"><i class="fas fa-times"></i></span>',
            '<span style="color: #28a745;"><i class="fas fa-check"></i></span>' if has_ton_tree else '<span style="color: #dc3545;"><i class="fas fa-times"></i></span>',
            '<span style="color: #28a745;"><i class="fas fa-check"></i></span>' if has_not_tree else '<span style="color: #dc3545;"><i class="fas fa-times"></i></span>'
        )
    
    inviter_stats.short_description = 'Статистика приглашающего'
    
    def invited_stats(self, obj):
        """Статистика приглашенного пользователя"""
        invited = obj.invited
        
        # Собираем данные о пользователе
        has_cf_tree = invited.trees.filter(type='CF').exists()
        has_ton_tree = invited.trees.filter(type='TON').exists()
        has_not_tree = invited.trees.filter(type='NOT').exists()
        
        # Количество заказов на P2P
        orders_count = invited.orders.count() if hasattr(invited, 'orders') else 0
        
        # Создаем HTML с информацией
        return format_html(
            '<div style="background-color: #f5f5f5; padding: 15px; border-radius: 10px; margin-top: 10px;">'
            '<h3 style="margin-top: 0; color: #0f7fd8;">Приглашенный: {}</h3>'
            '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">'
            '<div><strong>Telegram ID:</strong> {}</div>'
            '<div><strong>Дата регистрации:</strong> {}</div>'
            '<div><strong>Активность:</strong> {}</div>'
            '<div><strong>Ордеров на P2P:</strong> <span style="color: {}; font-weight: bold;">{}</span></div>'
            '</div>'
            '<div style="margin-top: 10px;">'
            '<strong>Балансы:</strong> '
            '<span style="color: #f9ca24; font-weight: bold;">{:.2f} CF</span>, '
            '<span style="color: #0f7fd8; font-weight: bold;">{:.8f} TON</span>, '
            '<span style="color: #9c88ff; font-weight: bold;">{:.2f} NOT</span>'
            '</div>'
            '<div style="margin-top: 10px;">'
            '<strong>Деревья:</strong> '
            '{} CF, {} TON, {} NOT'
            '</div>'
            '</div>',
            invited,
            invited.telegram_id,
            invited.date_joined.strftime('%d.%m.%Y'),
            self._get_user_activity_status(invited),
            '#28a745' if orders_count > 0 else '#6c757d',
            orders_count,
            invited.cf_balance,
            invited.ton_balance,
            invited.not_balance,
            '<span style="color: #28a745;"><i class="fas fa-check"></i></span>' if has_cf_tree else '<span style="color: #dc3545;"><i class="fas fa-times"></i></span>',
            '<span style="color: #28a745;"><i class="fas fa-check"></i></span>' if has_ton_tree else '<span style="color: #dc3545;"><i class="fas fa-times"></i></span>',
            '<span style="color: #28a745;"><i class="fas fa-check"></i></span>' if has_not_tree else '<span style="color: #dc3545;"><i class="fas fa-times"></i></span>'
        )
    
    invited_stats.short_description = 'Статистика приглашенного'
    
    def _get_user_activity_status(self, user):
        """Получить статус активности пользователя"""
        # Проверяем полив за последние сутки
        if user.last_watered and user.last_watered > timezone.now() - timedelta(days=1):
            return '<span style="color: #28a745;"><i class="fas fa-circle"></i> Активен</span>'
        
        # Проверяем полив за последнюю неделю
        if user.last_watered and user.last_watered > timezone.now() - timedelta(days=7):
            return '<span style="color: #ffc107;"><i class="fas fa-circle"></i> Умеренный</span>'
        
        # Проверяем полив за последний месяц
        if user.last_watered and user.last_watered > timezone.now() - timedelta(days=30):
            return '<span style="color: #dc3545;"><i class="fas fa-circle"></i> Редкий</span>'
        
        # Неактивен
        return '<span style="color: #6c757d;"><i class="fas fa-circle"></i> Неактивен</span>'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('inviter', 'invited')
    
    def give_bonus_to_inviters(self, request, queryset):
        """Выдача бонуса приглашающим"""
        from django.contrib.admin.helpers import ActionForm
        from django import forms
        
        class BonusForm(ActionForm):
            amount = forms.DecimalField(label='Количество CF', initial=50)
        
        self.action_form = BonusForm
        amount = request.POST.get('amount')
        
        if 'apply' in request.POST and amount:
            amount = float(amount)
            count = 0
            
            for referral in queryset:
                inviter = referral.inviter
                inviter.cf_balance += amount
                inviter.save()
                
                # Обновляем информацию о бонусе
                if referral.bonus_cf:
                    referral.bonus_cf += amount
                else:
                    referral.bonus_cf = amount
                referral.save()
                
                count += 1
            
            self.message_user(request, f'Успешно выдано {amount} CF {count} приглашающим пользователям.')
    
    give_bonus_to_inviters.short_description = "Выдать бонус приглашающим"
    
    def recalculate_bonuses(self, request, queryset):
        """Пересчет бонусов на основе активности приглашенных"""
        count = 0
        
        for referral in queryset:
            invited = referral.invited
            
            # Базовый бонус
            base_bonus = 50
            
            # Дополнительный бонус за активность приглашенного
            activity_bonus = 0
            
            # Проверяем наличие деревьев
            if invited.trees.filter(type='CF').exists():
                activity_bonus += 10
            
            if invited.trees.filter(type='TON').exists():
                activity_bonus += 20
            
            if invited.trees.filter(type='NOT').exists():
                activity_bonus += 30
            
            # Проверяем стейкинг
            if invited.staking_cf > 0:
                activity_bonus += 25
            
            # Проверяем активность на P2P
            if hasattr(invited, 'orders') and invited.orders.count() > 0:
                activity_bonus += 15
            
            # Обновляем информацию о бонусе
            referral.bonus_cf = base_bonus + activity_bonus
            referral.save()
            
            # Обновляем баланс приглашающего
            inviter = referral.inviter
            
            # Вычисляем разницу в бонусе
            old_bonus = referral.bonus_cf - (base_bonus + activity_bonus)
            
            if old_bonus != 0:
                inviter.cf_balance += (base_bonus + activity_bonus - old_bonus)
                inviter.save()
            
            count += 1
        
        self.message_user(request, f'Успешно пересчитаны бонусы для {count} реферальных связей.')
    
    recalculate_bonuses.short_description = "Пересчитать бонусы"
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }
