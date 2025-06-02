from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Count

from .models import ShopItem, Purchase

@admin.register(ShopItem)
class ShopItemAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели ShopItem
    """
    list_display = ('id', 'name', 'type_badge', 'price_with_token', 'duration_display', 
                   'purchases_count', 'is_active_icon', 'preview_image')
    list_filter = ('type', 'is_active', 'price_token_type')
    search_fields = ('name', 'description')
    readonly_fields = ('preview_image',)
    list_per_page = 20
    save_on_top = True
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'type', 'description', 'is_active')
        }),
        ('Цена', {
            'fields': ('price', 'price_token_type')
        }),
        ('Изображение', {
            'fields': ('image', 'preview_image')
        }),
        ('Дополнительные параметры', {
            'fields': ('duration',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_items', 'deactivate_items']
    
    def type_badge(self, obj):
        """Красивый значок для типа товара"""
        colors = {
            'auto_water': '#17a2b8',
            'fertilizer': '#28a745',
            'ton_tree': '#0f7fd8',
            'not_tree': '#9c88ff',
            'cf_slot': '#f9ca24',
        }
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
                         colors.get(obj.type, '#6c757d'), obj.get_type_display())
    
    type_badge.short_description = 'Тип'
    type_badge.admin_order_field = 'type'
    
    def price_with_token(self, obj):
        """Отображение цены с типом токена"""
        token_colors = {
            'CF': '#f9ca24',
            'TON': '#0f7fd8',
            'NOT': '#9c88ff'
        }
        color = token_colors.get(obj.price_token_type, '#6c757d')
        
        return format_html('<span style="font-weight: bold;">{}</span> <span style="color: {};">{}</span>', 
                         obj.price, color, obj.price_token_type)
    
    price_with_token.short_description = 'Цена'
    price_with_token.admin_order_field = 'price'
    
    def duration_display(self, obj):
        """Отображение длительности действия"""
        if not obj.duration:
            return format_html('<span style="color: #28a745;">Бессрочно</span>')
        
        if obj.duration < 24:
            return format_html('{} часов', obj.duration)
        
        days = obj.duration // 24
        hours = obj.duration % 24
        
        if hours == 0:
            return format_html('{} дней', days)
        
        return format_html('{} дней {} часов', days, hours)
    
    duration_display.short_description = 'Длительность'
    duration_display.admin_order_field = 'duration'
    
    def is_active_icon(self, obj):
        """Иконка активности товара"""
        if obj.is_active:
            return format_html('<span style="color: #28a745;"><i class="fas fa-check-circle"></i></span>')
        return format_html('<span style="color: #dc3545;"><i class="fas fa-times-circle"></i></span>')
    
    is_active_icon.short_description = 'Активен'
    is_active_icon.admin_order_field = 'is_active'
    
    def preview_image(self, obj):
        """Предпросмотр изображения товара"""
        if not obj.image:
            return format_html('<span style="color: #dc3545;">Нет изображения</span>')
        
        return format_html('<img src="{}" width="100" height="100" style="object-fit: contain;" />', obj.image)
    
    preview_image.short_description = 'Предпросмотр'
    
    def purchases_count(self, obj):
        """Количество покупок товара"""
        count = obj.purchases.count()
        url = reverse('admin:shop_purchase_changelist') + f'?item__id__exact={obj.id}'
        
        return format_html('<a href="{}" style="color: #0f7fd8; font-weight: bold;">{}</a>', url, count)
    
    purchases_count.short_description = 'Продаж'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).annotate(
            purchases_count=Count('purchases')
        )
    
    def activate_items(self, request, queryset):
        """Активация товаров"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Успешно активировано {updated} товаров.')
    
    activate_items.short_description = "Активировать выбранные товары"
    
    def deactivate_items(self, request, queryset):
        """Деактивация товаров"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Успешно деактивировано {updated} товаров.')
    
    deactivate_items.short_description = "Деактивировать выбранные товары"
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели Purchase
    """
    list_display = ('id', 'user_link', 'item_link', 'price_paid_with_token', 
                   'created_at', 'valid_until_display', 'is_active_status')
    list_filter = ('created_at', 'item__type', 'item__price_token_type')
    search_fields = ('user__username', 'user__telegram_id', 'item__name')
    readonly_fields = ('created_at', 'is_active_status')
    date_hierarchy = 'created_at'
    list_per_page = 20
    
    fieldsets = (
        ('Информация о покупке', {
            'fields': ('user', 'item', 'price_paid')
        }),
        ('Время действия', {
            'fields': ('created_at', 'valid_until', 'is_active_status')
        }),
    )
    
    actions = ['extend_duration']
    
    def user_link(self, obj):
        """Ссылка на пользователя"""
        url = reverse("admin:users_user_change", args=[obj.user.telegram_id])
        return format_html('<a href="{}">{} ({})</a>', 
                         url, obj.user.username, obj.user.telegram_id)
    
    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user__username'
    
    def item_link(self, obj):
        """Ссылка на товар"""
        url = reverse("admin:shop_shopitem_change", args=[obj.item.id])
        return format_html('<a href="{}">{} ({})</a>', 
                         url, obj.item.name, obj.item.get_type_display())
    
    item_link.short_description = 'Товар'
    item_link.admin_order_field = 'item__name'
    
    def price_paid_with_token(self, obj):
        """Отображение оплаченной цены с типом токена"""
        token_colors = {
            'CF': '#f9ca24',
            'TON': '#0f7fd8',
            'NOT': '#9c88ff'
        }
        color = token_colors.get(obj.item.price_token_type, '#6c757d')
        
        return format_html('<span style="font-weight: bold;">{}</span> <span style="color: {};">{}</span>', 
                         obj.price_paid, color, obj.item.price_token_type)
    
    price_paid_with_token.short_description = 'Оплачено'
    price_paid_with_token.admin_order_field = 'price_paid'
    
    def valid_until_display(self, obj):
        """Отображение срока действия"""
        if not obj.valid_until:
            return format_html('<span style="color: #28a745;">Бессрочно</span>')
        
        if obj.is_active():
            now = timezone.now()
            diff = obj.valid_until - now
            days = diff.days
            hours = diff.seconds // 3600
            
            return format_html('<span style="color: #28a745;">Еще {} дн. {} ч.</span>', days, hours)
        else:
            return format_html('<span style="color: #dc3545;">Истек {}</span>', 
                             obj.valid_until.strftime('%d.%m.%Y %H:%M'))
    
    valid_until_display.short_description = 'Действует до'
    valid_until_display.admin_order_field = 'valid_until'
    
    def is_active_status(self, obj):
        """Статус активности покупки"""
        if obj.is_active():
            return format_html('<span style="color: #28a745;"><i class="fas fa-check-circle"></i> Активна</span>')
        
        if not obj.valid_until:
            return format_html('<span style="color: #28a745;"><i class="fas fa-infinity"></i> Бессрочно</span>')
            
        return format_html('<span style="color: #dc3545;"><i class="fas fa-times-circle"></i> Истекла</span>')
    
    is_active_status.short_description = 'Статус'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user', 'item')
    
    def extend_duration(self, request, queryset):
        """Продление срока действия покупок"""
        extended = 0
        
        for purchase in queryset:
            if purchase.valid_until:
                if purchase.is_active():
                    # Продляем активную покупку на 7 дней
                    purchase.valid_until = purchase.valid_until + timezone.timedelta(days=7)
                else:
                    # Если истек срок, продляем от текущей даты
                    purchase.valid_until = timezone.now() + timezone.timedelta(days=7)
                    
                purchase.save()
                extended += 1
        
        self.message_user(request, f'Срок действия продлен для {extended} покупок на 7 дней.')
    
    extend_duration.short_description = "Продлить срок действия на 7 дней"
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }
