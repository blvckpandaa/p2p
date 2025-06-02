from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Count, F, Q
from datetime import timedelta

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели Notification
    """
    list_display = ('id', 'user_link', 'notification_type', 'notification_title', 
                   'notification_status', 'created_at', 'delivery_time')
    list_filter = ('type', 'status', 'created_at', 'sent_at', 'read_at')
    search_fields = ('user__username', 'user__telegram_id', 'title', 'message')
    readonly_fields = ('created_at', 'sent_at', 'read_at', 'message_preview')
    list_per_page = 30
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Информация об уведомлении', {
            'fields': ('user', 'type', 'title')
        }),
        ('Содержание', {
            'fields': ('message', 'message_preview')
        }),
        ('Статус доставки', {
            'fields': ('status', 'created_at', 'sent_at', 'read_at')
        }),
    )
    
    actions = ['mark_as_sent', 'mark_as_read', 'mark_as_pending', 'resend_notifications']
    
    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse("admin:users_user_change", args=[obj.user.telegram_id])
        return format_html('<a href="{}" style="color: #3a1a78; font-weight: bold;">{}</a>',
                         url, obj.user)
    
    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user__username'
    
    def notification_type(self, obj):
        """Отображение типа уведомления"""
        type_colors = {
            'watering': '#28a745',     # Зеленый
            'auto_water': '#17a2b8',   # Голубой
            'order': '#0f7fd8',        # Синий
            'staking': '#f9ca24',      # Желтый
            'referral': '#9c88ff',     # Фиолетовый
            'system': '#dc3545',       # Красный
        }
        color = type_colors.get(obj.type, '#6c757d')  # Серый по умолчанию
        
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
                         color, obj.get_type_display())
    
    notification_type.short_description = 'Тип'
    notification_type.admin_order_field = 'type'
    
    def notification_title(self, obj):
        """Отображение заголовка уведомления"""
        return format_html('<span style="font-weight: bold;">{}</span>', obj.title)
    
    notification_title.short_description = 'Заголовок'
    notification_title.admin_order_field = 'title'
    
    def notification_status(self, obj):
        """Отображение статуса уведомления"""
        status_colors = {
            'pending': '#ffc107',  # Желтый
            'sent': '#17a2b8',     # Голубой
            'read': '#28a745',     # Зеленый
            'failed': '#dc3545',   # Красный
        }
        color = status_colors.get(obj.status, '#6c757d')
        
        status_icons = {
            'pending': '<i class="fas fa-clock"></i>',
            'sent': '<i class="fas fa-check"></i>',
            'read': '<i class="fas fa-check-double"></i>',
            'failed': '<i class="fas fa-exclamation-triangle"></i>',
        }
        icon = status_icons.get(obj.status, '')
        
        return format_html('<span style="color: {};">{} {}</span>',
                         color, icon, obj.get_status_display())
    
    notification_status.short_description = 'Статус'
    notification_status.admin_order_field = 'status'
    
    def delivery_time(self, obj):
        """Время доставки уведомления"""
        if obj.status == 'pending':
            return format_html('<span style="color: #ffc107;">Ожидает отправки</span>')
        
        if obj.status == 'sent' and obj.sent_at:
            # Считаем время от создания до отправки
            delivery_seconds = (obj.sent_at - obj.created_at).total_seconds()
            
            if delivery_seconds < 60:
                return format_html('<span style="color: #28a745;">{:.1f} сек</span>', delivery_seconds)
            elif delivery_seconds < 3600:
                minutes = delivery_seconds / 60
                return format_html('<span style="color: #28a745;">{:.1f} мин</span>', minutes)
            else:
                hours = delivery_seconds / 3600
                return format_html('<span style="color: #ffc107;">{:.1f} ч</span>', hours)
        
        if obj.status == 'read' and obj.read_at and obj.sent_at:
            # Считаем время от отправки до прочтения
            read_seconds = (obj.read_at - obj.sent_at).total_seconds()
            
            if read_seconds < 60:
                return format_html('<span style="color: #28a745;">Прочитано через {:.1f} сек</span>', read_seconds)
            elif read_seconds < 3600:
                minutes = read_seconds / 60
                return format_html('<span style="color: #28a745;">Прочитано через {:.1f} мин</span>', minutes)
            else:
                hours = read_seconds / 3600
                return format_html('<span style="color: #ffc107;">Прочитано через {:.1f} ч</span>', hours)
        
        if obj.status == 'failed':
            return format_html('<span style="color: #dc3545;">Ошибка доставки</span>')
        
        return '-'
    
    delivery_time.short_description = 'Время доставки'
    
    def message_preview(self, obj):
        """Предпросмотр сообщения с форматированием"""
        if not obj.message:
            return '-'
        
        # Заменяем специальные HTML-символы для безопасного отображения
        message = obj.message.replace('<', '&lt;').replace('>', '&gt;')
        
        # Добавляем базовое форматирование
        message = message.replace('\n', '<br>')
        
        # Подсвечиваем ключевые слова в зависимости от типа уведомления
        highlight_words = {
            'watering': ['полив', 'дерево', 'урожай'],
            'auto_water': ['авто-полив', 'автоматический', 'подписка'],
            'order': ['ордер', 'продажа', 'покупка', 'транзакция', 'P2P'],
            'staking': ['стейкинг', 'вознаграждение', 'проценты', 'доход'],
            'referral': ['реферал', 'приглашение', 'бонус', 'друг'],
            'system': ['система', 'обновление', 'внимание', 'важно'],
        }
        
        if obj.type in highlight_words:
            for word in highlight_words[obj.type]:
                message = message.replace(
                    word, 
                    f'<span style="background-color: #f9ca24; color: #000; padding: 0 3px; border-radius: 3px;">{word}</span>'
                )
        
        return format_html('<div style="background-color: #f5f5f5; padding: 15px; border-radius: 10px; margin-top: 10px;">'
                         '<div style="color: #333;">{}</div>'
                         '</div>', message)
    
    message_preview.short_description = 'Предпросмотр сообщения'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user')
    
    def mark_as_sent(self, request, queryset):
        """Отметить выбранные уведомления как отправленные"""
        pending = queryset.filter(status='pending')
        now = timezone.now()
        updated = pending.update(status='sent', sent_at=now)
        
        self.message_user(request, f'Успешно отмечено {updated} уведомлений как отправленные.')
    
    mark_as_sent.short_description = "Отметить как отправленные"
    
    def mark_as_read(self, request, queryset):
        """Отметить выбранные уведомления как прочитанные"""
        not_read = queryset.exclude(status='read')
        now = timezone.now()
        
        # Если уведомление не было отправлено, отмечаем его как отправленное
        for notification in not_read:
            if not notification.sent_at:
                notification.sent_at = now
            notification.read_at = now
            notification.status = 'read'
            notification.save()
        
        self.message_user(request, f'Успешно отмечено {not_read.count()} уведомлений как прочитанные.')
    
    mark_as_read.short_description = "Отметить как прочитанные"
    
    def mark_as_pending(self, request, queryset):
        """Отметить выбранные уведомления как ожидающие отправки"""
        updated = queryset.update(status='pending', sent_at=None, read_at=None)
        
        self.message_user(request, f'Успешно отмечено {updated} уведомлений как ожидающие отправки.')
    
    mark_as_pending.short_description = "Отметить как ожидающие отправки"
    
    def resend_notifications(self, request, queryset):
        """Повторная отправка уведомлений"""
        # Отмечаем уведомления как ожидающие отправки
        updated = queryset.update(status='pending', sent_at=None, read_at=None)
        
        # В реальном приложении здесь был бы код для запуска фоновой задачи отправки
        self.message_user(request, f'Поставлено в очередь на повторную отправку {updated} уведомлений.')
    
    resend_notifications.short_description = "Отправить повторно"
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }
