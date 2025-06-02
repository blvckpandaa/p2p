from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Count, F, Q
from datetime import timedelta

from .models import Staking


@admin.register(Staking)
class StakingAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели Staking
    """
    list_display = ('id', 'user_link', 'amount_display', 'token_badge', 'reward_display',
                   'roi_percent', 'status_badge', 'time_remaining', 'start_date', 'end_date')
    list_filter = ('status', 'token_type', 'start_date', 'end_date')
    search_fields = ('user__username', 'user__telegram_id', 'amount')
    readonly_fields = ('start_date', 'claimed_date', 'user_balance_display')
    list_per_page = 20
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Информация о стейкинге', {
            'fields': ('user', 'status', 'user_balance_display')
        }),
        ('Финансовые детали', {
            'fields': ('amount', 'token_type', 'reward_amount')
        }),
        ('Временные метки', {
            'fields': ('start_date', 'end_date', 'claimed_date')
        }),
    )
    
    actions = ['complete_staking', 'cancel_staking', 'extend_staking', 'add_reward']
    
    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse("admin:users_user_change", args=[obj.user.telegram_id])
        return format_html('<a href="{}" style="color: #3a1a78; font-weight: bold;">{}</a>',
                         url, obj.user)
    
    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user__username'
    
    def amount_display(self, obj):
        """Отображение суммы стейкинга"""
        return format_html('<span style="font-weight: bold;">{}</span>', obj.amount)
    
    amount_display.short_description = 'Сумма'
    amount_display.admin_order_field = 'amount'
    
    def token_badge(self, obj):
        """Значок для типа токена"""
        colors = {
            'CF': '#f9ca24',
            'TON': '#0f7fd8',
            'NOT': '#9c88ff'
        }
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
                         colors.get(obj.token_type, '#6c757d'), obj.token_type)
    
    token_badge.short_description = 'Токен'
    token_badge.admin_order_field = 'token_type'
    
    def reward_display(self, obj):
        """Отображение суммы вознаграждения"""
        if obj.reward_amount:
            return format_html('<span style="color: #28a745; font-weight: bold;">{}</span>', obj.reward_amount)
        
        # Рассчитываем примерное вознаграждение (например, 5% в месяц)
        days = (obj.end_date - obj.start_date).days
        monthly_roi = 0.05  # 5% в месяц
        daily_roi = monthly_roi / 30
        estimated_reward = obj.amount * daily_roi * days
        
        return format_html('<span style="color: #ffc107; font-weight: bold;">~{:.2f}</span> '
                         '<small>(расчетное)</small>', estimated_reward)
    
    reward_display.short_description = 'Вознаграждение'
    
    def roi_percent(self, obj):
        """Процент возврата инвестиций"""
        if not obj.reward_amount:
            return '-'
        
        roi = (obj.reward_amount / obj.amount) * 100
        return format_html('<span style="color: #28a745; font-weight: bold;">{:.2f}%</span>', roi)
    
    roi_percent.short_description = 'ROI'
    
    def status_badge(self, obj):
        """Значок для статуса стейкинга"""
        colors = {
            'active': '#28a745',
            'completed': '#0f7fd8',
            'claimed': '#f9ca24'
        }
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
                         colors.get(obj.status, '#6c757d'), obj.get_status_display())
    
    status_badge.short_description = 'Статус'
    status_badge.admin_order_field = 'status'
    
    def time_remaining(self, obj):
        """Оставшееся время стейкинга"""
        if obj.status != 'active':
            return '-'
        
        now = timezone.now()
        if now > obj.end_date:
            return format_html('<span style="color: #dc3545;">Истек</span>')
        
        days_left = (obj.end_date - now).days
        hours_left = ((obj.end_date - now).seconds // 3600)
        
        if days_left > 0:
            return format_html('<span style="color: #28a745;">{} дн. {} ч.</span>', days_left, hours_left)
        return format_html('<span style="color: #ffc107;">{} ч.</span>', hours_left)
    
    time_remaining.short_description = 'Осталось'
    
    def user_balance_display(self, obj):
        """Отображение баланса пользователя"""
        user = obj.user
        token_color = '#f9ca24' if obj.token_type == 'CF' else '#0f7fd8' if obj.token_type == 'TON' else '#9c88ff'
        balance = user.cf_balance if obj.token_type == 'CF' else user.ton_balance if obj.token_type == 'TON' else user.not_balance
        
        return format_html('<div style="margin-top: 10px; padding: 10px; background-color: rgba(255,255,255,0.1); border-radius: 10px;">'
                         '<strong>Текущий баланс:</strong> <span style="color: {}; font-weight: bold;">{} {}</span>'
                         '</div>', token_color, balance, obj.token_type)
    
    user_balance_display.short_description = 'Баланс пользователя'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user')
    
    def complete_staking(self, request, queryset):
        """Завершение стейкинга"""
        active_stakings = queryset.filter(status='active')
        count = active_stakings.count()
        
        for staking in active_stakings:
            # Определяем награду (если не установлена)
            if not staking.reward_amount:
                days = (staking.end_date - staking.start_date).days
                monthly_roi = 0.05  # 5% в месяц
                daily_roi = monthly_roi / 30
                staking.reward_amount = staking.amount * daily_roi * days
            
            # Возвращаем средства пользователю + награду
            user = staking.user
            if staking.token_type == 'CF':
                user.cf_balance += staking.amount + staking.reward_amount
            elif staking.token_type == 'TON':
                user.ton_balance += staking.amount + staking.reward_amount
            elif staking.token_type == 'NOT':
                user.not_balance += staking.amount + staking.reward_amount
            
            # Обновляем статус стейкинга
            staking.status = 'claimed'
            staking.claimed_date = timezone.now()
            
            # Сохраняем изменения
            user.save()
            staking.save()
        
        self.message_user(request, f'Успешно завершено {count} стейкингов. Средства возвращены пользователям.')
    
    complete_staking.short_description = "Завершить стейкинг и выплатить награду"
    
    def cancel_staking(self, request, queryset):
        """Отмена стейкинга"""
        active_stakings = queryset.filter(status='active')
        count = active_stakings.count()
        
        for staking in active_stakings:
            # Возвращаем только вложенные средства без награды
            user = staking.user
            if staking.token_type == 'CF':
                user.cf_balance += staking.amount
            elif staking.token_type == 'TON':
                user.ton_balance += staking.amount
            elif staking.token_type == 'NOT':
                user.not_balance += staking.amount
            
            # Обновляем статус стейкинга
            staking.status = 'completed'
            staking.claimed_date = timezone.now()
            
            # Сохраняем изменения
            user.save()
            staking.save()
        
        self.message_user(request, f'Успешно отменено {count} стейкингов. Средства возвращены пользователям без награды.')
    
    cancel_staking.short_description = "Отменить стейкинг (возврат без награды)"
    
    def extend_staking(self, request, queryset):
        """Продление срока стейкинга"""
        from django.contrib.admin.helpers import ActionForm
        from django import forms
        
        class StakingExtendForm(ActionForm):
            days = forms.IntegerField(label='Количество дней')
        
        self.action_form = StakingExtendForm
        days = request.POST.get('days')
        
        if 'apply' in request.POST and days:
            days = int(days)
            active_stakings = queryset.filter(status='active')
            updated = 0
            
            for staking in active_stakings:
                staking.end_date = staking.end_date + timedelta(days=days)
                staking.save()
                updated += 1
            
            self.message_user(request, f'Срок стейкинга продлен на {days} дней для {updated} стейкингов.')
    
    extend_staking.short_description = "Продлить стейкинг"
    
    def add_reward(self, request, queryset):
        """Добавление дополнительной награды"""
        from django.contrib.admin.helpers import ActionForm
        from django import forms
        
        class RewardForm(ActionForm):
            amount = forms.DecimalField(label='Сумма награды')
        
        self.action_form = RewardForm
        amount = request.POST.get('amount')
        
        if 'apply' in request.POST and amount:
            amount = float(amount)
            active_stakings = queryset.filter(status='active')
            updated = 0
            
            for staking in active_stakings:
                if staking.reward_amount:
                    staking.reward_amount += amount
                else:
                    staking.reward_amount = amount
                staking.save()
                updated += 1
            
            self.message_user(request, f'Добавлена награда {amount} для {updated} стейкингов.')
    
    add_reward.short_description = "Добавить награду"
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }
