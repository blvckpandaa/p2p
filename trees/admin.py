from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Count, F, Q
from datetime import timedelta

from .models import Tree


@admin.register(Tree)
class TreeAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели Tree
    """
    list_display = ('id', 'user_link', 'tree_type', 'tree_level', 'income_per_hour_display', 
                   'branches_collected_display', 'watering_status', 'fertilizer_status', 'created_at')
    list_filter = ('type', 'level', 'created_at')
    search_fields = ('user__username', 'user__telegram_id')
    readonly_fields = ('created_at', 'last_watered', 'fertilized_until', 'tree_visualization')
    list_per_page = 20
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Информация о дереве', {
            'fields': ('user', 'type', 'level', 'tree_visualization')
        }),
        ('Доходность', {
            'fields': ('income_per_hour', 'branches_collected')
        }),
        ('Статусы', {
            'fields': ('last_watered', 'fertilized_until')
        }),
        ('Временные метки', {
            'fields': ('created_at',)
        }),
    )
    
    actions = ['water_trees', 'fertilize_trees', 'level_up_trees', 'reset_branches']
    
    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse("admin:users_user_change", args=[obj.user.telegram_id])
        return format_html('<a href="{}" style="color: #3a1a78; font-weight: bold;">{}</a>',
                         url, obj.user)
    
    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user__username'
    
    def tree_type(self, obj):
        """Отображение типа дерева с цветом"""
        colors = {
            'CF': '#f9ca24',
            'TON': '#0f7fd8',
            'NOT': '#9c88ff'
        }
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
                         colors.get(obj.type, '#6c757d'), obj.get_type_display())
    
    tree_type.short_description = 'Тип'
    tree_type.admin_order_field = 'type'
    
    def tree_level(self, obj):
        """Отображение уровня дерева"""
        level_colors = {
            1: '#28a745',  # Зеленый для начального уровня
            2: '#17a2b8',  # Голубой
            3: '#0f7fd8',  # Синий
            4: '#9c88ff',  # Фиолетовый
            5: '#f9ca24',  # Желтый
        }
        color = level_colors.get(obj.level, '#dc3545')  # Красный для высоких уровней
        
        stars = '★' * obj.level
        return format_html('<span style="color: {}; font-weight: bold;">Lvl {} {}</span>',
                         color, obj.level, stars)
    
    tree_level.short_description = 'Уровень'
    tree_level.admin_order_field = 'level'
    
    def income_per_hour_display(self, obj):
        """Отображение дохода в час"""
        return format_html('<span style="color: #28a745; font-weight: bold;">+{}/час</span>', obj.income_per_hour)
    
    income_per_hour_display.short_description = 'Доход'
    income_per_hour_display.admin_order_field = 'income_per_hour'
    
    def branches_collected_display(self, obj):
        """Отображение собранных веток"""
        if obj.branches_collected > 0:
            return format_html('<span style="color: #f9ca24; font-weight: bold;">{}</span>', obj.branches_collected)
        return format_html('<span style="color: #6c757d;">0</span>')
    
    branches_collected_display.short_description = 'Ветки'
    branches_collected_display.admin_order_field = 'branches_collected'
    
    def watering_status(self, obj):
        """Статус полива"""
        if not obj.last_watered:
            return format_html('<span style="color: #dc3545;"><i class="fas fa-tint-slash"></i> Не полито</span>')
        
        # Проверяем, полито ли дерево (предполагаем, что полив действует 5 часов)
        now = timezone.now()
        watering_duration = 5  # часов
        watering_expires = obj.last_watered + timedelta(hours=watering_duration)
        
        if now < watering_expires:
            hours_left = int((watering_expires - now).total_seconds() / 3600)
            minutes_left = int(((watering_expires - now).total_seconds() % 3600) / 60)
            
            return format_html('<span style="color: #28a745;"><i class="fas fa-tint"></i> Полито</span> '
                             '<small>(еще {}ч {}мин)</small>', hours_left, minutes_left)
        
        time_since = now - obj.last_watered
        hours_ago = int(time_since.total_seconds() / 3600)
        
        return format_html('<span style="color: #ffc107;"><i class="fas fa-tint-slash"></i> Не полито</span> '
                         '<small>({}ч назад)</small>', hours_ago)
    
    watering_status.short_description = 'Полив'
    
    def fertilizer_status(self, obj):
        """Статус удобрения"""
        if not obj.fertilized_until:
            return format_html('<span style="color: #dc3545;"><i class="fas fa-seedling"></i> Не удобрено</span>')
        
        now = timezone.now()
        
        if now < obj.fertilized_until:
            days_left = (obj.fertilized_until - now).days
            hours_left = int(((obj.fertilized_until - now).total_seconds() % (24 * 3600)) / 3600)
            
            return format_html('<span style="color: #28a745;"><i class="fas fa-seedling"></i> Удобрено</span> '
                             '<small>(еще {}д {}ч)</small>', days_left, hours_left)
        
        time_since = now - obj.fertilized_until
        days_ago = time_since.days
        
        return format_html('<span style="color: #ffc107;"><i class="fas fa-seedling"></i> Не удобрено</span> '
                         '<small>(истекло {}д назад)</small>', days_ago)
    
    fertilizer_status.short_description = 'Удобрение'
    
    def tree_visualization(self, obj):
        """Визуализация дерева"""
        tree_colors = {
            'CF': ('Желтый', '#f9ca24'),
            'TON': ('Синий', '#0f7fd8'),
            'NOT': ('Фиолетовый', '#9c88ff')
        }
        
        tree_color_name, tree_color_hex = tree_colors.get(obj.type, ('Зеленый', '#28a745'))
        
        # Эмодзи дерева для разных уровней
        tree_emoji = {
            1: '🌱',  # Росток
            2: '🌿',  # Молодое растение
            3: '🌲',  # Молодое дерево
            4: '🌳',  # Взрослое дерево
            5: '🌴',  # Большое дерево
        }
        
        emoji = tree_emoji.get(obj.level, '🌳')
        
        # Генерируем ASCII-арт дерево
        tree_art = [
            '    *    ',
            '   ***   ',
            '  *****  ',
            ' ******* ',
            '    |    ',
            '    |    ',
            '~~~~~~~~~'
        ]
        
        return format_html(
            '<div style="background-color: #f5f5f5; padding: 15px; border-radius: 10px; margin-top: 10px;">'
            '<div style="font-size: 50px; text-align: center;">{}</div>'
            '<div style="margin-top: 10px; text-align: center;">'
            '<pre style="color: {}; font-weight: bold;">{}</pre>'
            '</div>'
            '<div style="margin-top: 10px;">'
            '<strong>Тип:</strong> {} ({})<br>'
            '<strong>Уровень:</strong> {}<br>'
            '<strong>Доход:</strong> {} в час<br>'
            '<strong>Накоплено веток:</strong> {}<br>'
            '</div>'
            '</div>',
            emoji,
            tree_color_hex, '\n'.join(tree_art),
            obj.get_type_display(), tree_color_name,
            obj.level,
            obj.income_per_hour,
            obj.branches_collected
        )
    
    tree_visualization.short_description = 'Визуализация дерева'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user')
    
    def water_trees(self, request, queryset):
        """Полив деревьев"""
        now = timezone.now()
        count = queryset.count()
        
        queryset.update(last_watered=now)
        
        self.message_user(request, f'Успешно полито {count} деревьев.')
    
    water_trees.short_description = "Полить деревья"
    
    def fertilize_trees(self, request, queryset):
        """Удобрение деревьев"""
        from django.contrib.admin.helpers import ActionForm
        from django import forms
        
        class FertilizerForm(ActionForm):
            days = forms.IntegerField(label='Количество дней', initial=1)
        
        self.action_form = FertilizerForm
        days = request.POST.get('days')
        
        if 'apply' in request.POST and days:
            days = int(days)
            now = timezone.now()
            count = queryset.count()
            
            queryset.update(fertilized_until=now + timedelta(days=days))
            
            self.message_user(request, f'Успешно удобрено {count} деревьев на {days} дней.')
    
    fertilize_trees.short_description = "Удобрить деревья"
    
    def level_up_trees(self, request, queryset):
        """Повышение уровня деревьев"""
        count = queryset.count()
        
        for tree in queryset:
            tree.level += 1
            # Увеличиваем доход в зависимости от уровня
            tree.income_per_hour = tree.income_per_hour * 1.5
            tree.save()
        
        self.message_user(request, f'Успешно повышен уровень для {count} деревьев.')
    
    level_up_trees.short_description = "Повысить уровень"
    
    def reset_branches(self, request, queryset):
        """Сброс собранных веток"""
        count = queryset.count()
        
        queryset.update(branches_collected=0)
        
        self.message_user(request, f'Успешно сброшено количество веток для {count} деревьев.')
    
    reset_branches.short_description = "Сбросить ветки"
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }
