from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from decimal import Decimal

from .models import Order, Transaction, Message


class MessageInline(admin.TabularInline):
    """
    Инлайн для отображения сообщений внутри транзакции
    """
    model = Message
    extra = 0
    readonly_fields = ('sender', 'content', 'is_read', 'created_at')
    fields = ('sender', 'content', 'is_read', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели Order
    """
    list_display = ('id', 'user_link', 'type_badge', 'token_badge', 'amount', 'price_per_unit', 
                   'total_price', 'status_badge', 'created_at', 'expires_at', 'active_indicator')
    list_filter = ('type', 'token_type', 'status', 'created_at', 'expires_at')
    search_fields = ('user__username', 'user__telegram_id', 'payment_details', 'id')
    readonly_fields = ('created_at', 'updated_at', 'total_price_display')
    list_per_page = 20
    date_hierarchy = 'created_at'
    save_on_top = True
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'type', 'token_type', 'status')
        }),
        ('Финансовые детали', {
            'fields': ('amount', 'price_per_unit', 'min_amount', 'total_price_display')
        }),
        ('Дополнительные сведения', {
            'fields': ('payment_details', 'expires_at', 'created_at', 'updated_at')
        }),
    )
    
    actions = ['activate_orders', 'cancel_orders', 'extend_expiration']
    
    def total_price_display(self, obj):
        """Отображение полной стоимости ордера"""
        return format_html('<span style="color: #0f7fd8; font-weight: bold;">{} TON</span>', 
                         obj.amount * obj.price_per_unit)
    
    total_price_display.short_description = 'Общая стоимость'
    
    def user_link(self, obj):
        """Ссылка на пользователя с информацией о балансе"""
        url = reverse("admin:users_user_change", args=[obj.user.id])
        balance_info = ""
        
        if obj.token_type == 'CF':
            balance_info = f" (CF: {obj.user.cf_balance})"
        elif obj.token_type == 'TON':
            balance_info = f" (TON: {obj.user.ton_balance})"
        elif obj.token_type == 'NOT':
            balance_info = f" (NOT: {obj.user.not_balance})"
        
        return format_html('<a href="{}" title="Баланс пользователя: {}">{} {}</a>', 
                         url, balance_info, obj.user.username, obj.user.telegram_id)
    
    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user__username'
    
    def type_badge(self, obj):
        """Красивый значок для типа ордера"""
        if obj.type == 'buy':
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 10px;">'
                             '<i class="fas fa-arrow-down"></i> Покупка</span>')
        else:
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 10px;">'
                             '<i class="fas fa-arrow-up"></i> Продажа</span>')
    
    type_badge.short_description = 'Тип'
    type_badge.admin_order_field = 'type'
    
    def token_badge(self, obj):
        """Красивый значок для типа токена"""
        colors = {
            'CF': '#f9ca24',
            'TON': '#0f7fd8',
            'NOT': '#9c88ff'
        }
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
                         colors.get(obj.token_type, '#6c757d'), obj.token_type)
    
    token_badge.short_description = 'Токен'
    token_badge.admin_order_field = 'token_type'
    
    def status_badge(self, obj):
        """Красивый значок для статуса ордера"""
        colors = {
            'active': '#28a745',
            'completed': '#0f7fd8',
            'cancelled': '#dc3545',
            'expired': '#6c757d'
        }
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
                         colors.get(obj.status, '#6c757d'), obj.get_status_display())
    
    status_badge.short_description = 'Статус'
    status_badge.admin_order_field = 'status'
    
    def active_indicator(self, obj):
        """Индикатор активности ордера"""
        if obj.status == 'active' and not obj.is_expired:
            return format_html('<span style="color: green;"><i class="fas fa-check-circle"></i></span>')
        return format_html('<span style="color: red;"><i class="fas fa-times-circle"></i></span>')
    
    active_indicator.short_description = 'Активен'
    
    def total_price(self, obj):
        """Расчет общей стоимости ордера"""
        total = obj.amount * obj.price_per_unit
        return format_html('{} TON', total)
    
    total_price.short_description = 'Общая стоимость'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        queryset = super().get_queryset(request)
        return queryset.select_related('user')
    
    def activate_orders(self, request, queryset):
        """Активация выбранных ордеров"""
        updated = queryset.update(status='active', expires_at=timezone.now() + timezone.timedelta(days=3))
        self.message_user(request, f'Успешно активировано {updated} ордеров.')
    
    activate_orders.short_description = "Активировать выбранные ордера"
    
    def cancel_orders(self, request, queryset):
        """Отмена выбранных ордеров"""
        active_orders = queryset.filter(status='active')
        count = active_orders.count()
        
        # Для ордеров на продажу нужно вернуть средства пользователям
        for order in active_orders:
            if order.type == 'sell':
                user = order.user
                if order.token_type == 'CF':
                    user.cf_balance += order.amount
                elif order.token_type == 'TON':
                    user.ton_balance += order.amount
                elif order.token_type == 'NOT':
                    user.not_balance += order.amount
                user.save()
        
        # Отмечаем ордера как отмененные
        active_orders.update(status='cancelled')
        
        self.message_user(request, f'Успешно отменено {count} ордеров. Средства возвращены пользователям.')
    
    cancel_orders.short_description = "Отменить выбранные ордера и вернуть средства"
    
    def extend_expiration(self, request, queryset):
        """Продление срока действия ордеров"""
        active_orders = queryset.filter(status='active')
        updated = active_orders.update(expires_at=timezone.now() + timezone.timedelta(days=3))
        self.message_user(request, f'Срок действия продлен для {updated} ордеров.')
    
    extend_expiration.short_description = "Продлить срок действия на 3 дня"
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели Transaction
    """
    list_display = ('id', 'order_link', 'buyer_link', 'seller_link', 'token_badge', 
                   'amount', 'price_per_unit', 'total_amount', 'commission', 
                   'status_badge', 'created_at', 'message_count')
    list_filter = ('token_type', 'status', 'created_at')
    search_fields = ('buyer__username', 'seller__username', 'buyer__telegram_id', 'seller__telegram_id', 'id')
    readonly_fields = ('created_at', 'updated_at', 'order', 'buyer', 'seller', 'amount', 
                      'price_per_unit', 'token_type', 'commission', 'total_with_commission_display')
    list_per_page = 20
    date_hierarchy = 'created_at'
    inlines = [MessageInline]
    
    fieldsets = (
        ('Информация о сделке', {
            'fields': ('order', 'buyer', 'seller', 'status')
        }),
        ('Финансовые детали', {
            'fields': ('amount', 'price_per_unit', 'token_type', 'commission', 'total_with_commission_display')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['complete_transactions', 'cancel_transactions']
    
    def total_with_commission_display(self, obj):
        """Отображение полной стоимости с комиссией"""
        total = obj.amount * obj.price_per_unit
        total_with_commission = total + obj.commission
        return format_html('<span style="color: #0f7fd8; font-weight: bold;">{} TON</span> '
                         '(Базовая стоимость: <span style="color: #28a745;">{} TON</span>, '
                         'Комиссия: <span style="color: #dc3545;">{} TON</span>)', 
                         total_with_commission, total, obj.commission)
    
    total_with_commission_display.short_description = 'Общая стоимость с комиссией'
    
    def order_link(self, obj):
        """Ссылка на ордер"""
        url = reverse("admin:p2p_order_change", args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.id)
    
    order_link.short_description = 'Ордер'
    order_link.admin_order_field = 'order'
    
    def buyer_link(self, obj):
        """Ссылка на покупателя"""
        url = reverse("admin:users_user_change", args=[obj.buyer.id])
        return format_html('<a href="{}" style="color: #28a745;"><i class="fas fa-user"></i> {} ({})</a>', 
                         url, obj.buyer.username, obj.buyer.telegram_id)
    
    buyer_link.short_description = 'Покупатель'
    buyer_link.admin_order_field = 'buyer__username'
    
    def seller_link(self, obj):
        """Ссылка на продавца"""
        url = reverse("admin:users_user_change", args=[obj.seller.id])
        return format_html('<a href="{}" style="color: #dc3545;"><i class="fas fa-user"></i> {} ({})</a>', 
                         url, obj.seller.username, obj.seller.telegram_id)
    
    seller_link.short_description = 'Продавец'
    seller_link.admin_order_field = 'seller__username'
    
    def token_badge(self, obj):
        """Красивый значок для типа токена"""
        colors = {
            'CF': '#f9ca24',
            'TON': '#0f7fd8',
            'NOT': '#9c88ff'
        }
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
                         colors.get(obj.token_type, '#6c757d'), obj.token_type)
    
    token_badge.short_description = 'Токен'
    token_badge.admin_order_field = 'token_type'
    
    def status_badge(self, obj):
        """Красивый значок для статуса транзакции"""
        colors = {
            'pending': '#ffc107',
            'paid': '#17a2b8',
            'completed': '#28a745',
            'cancelled': '#dc3545'
        }
        return format_html('<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
                         colors.get(obj.status, '#6c757d'), obj.get_status_display())
    
    status_badge.short_description = 'Статус'
    status_badge.admin_order_field = 'status'
    
    def total_amount(self, obj):
        """Расчет общей стоимости транзакции"""
        total = obj.amount * obj.price_per_unit
        return format_html('{} TON', total)
    
    total_amount.short_description = 'Общая сумма'
    
    def message_count(self, obj):
        """Количество сообщений в транзакции"""
        count = obj.message_set.count()
        if count > 0:
            return format_html('<span style="background-color: #17a2b8; color: white; padding: 2px 6px; border-radius: 10px;">{}</span>', count)
        return '0'
    
    message_count.short_description = 'Сообщения'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        queryset = super().get_queryset(request)
        return queryset.select_related('order', 'buyer', 'seller').annotate(
            message_count=Count('message')
        )
    
    def complete_transactions(self, request, queryset):
        """Завершение выбранных транзакций"""
        pending_transactions = queryset.filter(status='paid')
        count = pending_transactions.count()
        
        for transaction in pending_transactions:
            # Выполняем обмен средствами
            buyer = transaction.buyer
            seller = transaction.seller
            amount = transaction.amount
            price = amount * transaction.price_per_unit
            
            if transaction.token_type == 'CF':
                if transaction.order.type == 'sell':
                    # Продавец продает CF, покупатель получает CF
                    buyer.cf_balance += amount
                    buyer.ton_balance -= price
                    seller.ton_balance += price
                else:  # buy order
                    # Продавец продает TON за CF, покупатель получает TON
                    seller.cf_balance += amount
                    seller.ton_balance -= price
                    buyer.ton_balance += price
            elif transaction.token_type == 'TON':
                if transaction.order.type == 'sell':
                    # Продавец продает TON, покупатель получает TON
                    buyer.ton_balance += amount
                    buyer.cf_balance -= price
                    seller.cf_balance += price
                else:  # buy order
                    # Продавец продает CF за TON, покупатель получает CF
                    seller.ton_balance += amount
                    seller.cf_balance -= price
                    buyer.cf_balance += price
            elif transaction.token_type == 'NOT':
                if transaction.order.type == 'sell':
                    # Продавец продает NOT, покупатель получает NOT
                    buyer.not_balance += amount
                    buyer.ton_balance -= price
                    seller.ton_balance += price
                else:  # buy order
                    # Продавец продает TON за NOT, покупатель получает TON
                    seller.not_balance += amount
                    seller.ton_balance -= price
                    buyer.ton_balance += price
            
            buyer.save()
            seller.save()
        
        # Отмечаем транзакции как завершенные
        pending_transactions.update(status='completed')
        
        self.message_user(request, f'Успешно завершено {count} транзакций. Средства переведены между пользователями.')
    
    complete_transactions.short_description = "Завершить выбранные транзакции и перевести средства"
    
    def cancel_transactions(self, request, queryset):
        """Отмена выбранных транзакций"""
        active_transactions = queryset.filter(Q(status='pending') | Q(status='paid'))
        count = active_transactions.count()
        
        # Отмечаем транзакции как отмененные
        active_transactions.update(status='cancelled')
        
        self.message_user(request, f'Успешно отменено {count} транзакций.')
    
    cancel_transactions.short_description = "Отменить выбранные транзакции"
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Административный интерфейс для модели Message
    """
    list_display = ('id', 'transaction_link', 'sender_link', 'recipient_display', 
                   'short_content', 'is_read_icon', 'created_at')
    list_filter = ('is_read', 'created_at', ('sender', admin.RelatedOnlyFieldListFilter))
    search_fields = ('content', 'sender__username', 'transaction__id')
    readonly_fields = ('created_at', 'transaction', 'sender', 'content')
    list_per_page = 30
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Информация о сообщении', {
            'fields': ('transaction', 'sender', 'content')
        }),
        ('Статус', {
            'fields': ('is_read', 'created_at')
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def transaction_link(self, obj):
        """Ссылка на транзакцию"""
        url = reverse("admin:p2p_transaction_change", args=[obj.transaction.id])
        return format_html('<a href="{}">{}</a>', url, obj.transaction.id)
    
    transaction_link.short_description = 'Транзакция'
    transaction_link.admin_order_field = 'transaction'
    
    def sender_link(self, obj):
        """Ссылка на отправителя"""
        url = reverse("admin:users_user_change", args=[obj.sender.id])
        if obj.sender == obj.transaction.buyer:
            color = '#28a745'  # Зеленый для покупателя
            role = 'Покупатель'
        else:
            color = '#dc3545'  # Красный для продавца
            role = 'Продавец'
            
        return format_html('<a href="{}" style="color: {};" title="{}">'
                         '<i class="fas fa-user"></i> {} ({})</a>', 
                         url, color, role, obj.sender.username, obj.sender.telegram_id)
    
    sender_link.short_description = 'Отправитель'
    sender_link.admin_order_field = 'sender__username'
    
    def recipient_display(self, obj):
        """Отображение получателя"""
        recipient = obj.recipient
        if recipient:
            url = reverse("admin:users_user_change", args=[recipient.id])
            if recipient == obj.transaction.buyer:
                color = '#28a745'  # Зеленый для покупателя
                role = 'Покупатель'
            else:
                color = '#dc3545'  # Красный для продавца
                role = 'Продавец'
                
            return format_html('<a href="{}" style="color: {};" title="{}">'
                             '<i class="fas fa-user"></i> {} ({})</a>', 
                             url, color, role, recipient.username, recipient.telegram_id)
        return "-"
    
    recipient_display.short_description = 'Получатель'
    
    def short_content(self, obj):
        """Сокращенное содержание сообщения"""
        if len(obj.content) > 50:
            return format_html('<span title="{}">{}</span>',
                             obj.content, f"{obj.content[:50]}...")
        return obj.content
    
    short_content.short_description = 'Сообщение'
    
    def is_read_icon(self, obj):
        """Иконка для статуса прочтения"""
        if obj.is_read:
            return format_html('<span style="color: #28a745;"><i class="fas fa-check-double"></i></span>')
        return format_html('<span style="color: #dc3545;"><i class="fas fa-check"></i></span>')
    
    is_read_icon.short_description = 'Прочитано'
    is_read_icon.admin_order_field = 'is_read'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('transaction', 'sender', 
                                                          'transaction__buyer', 'transaction__seller')
    
    def mark_as_read(self, request, queryset):
        """Отметить выбранные сообщения как прочитанные"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} сообщений отмечено как прочитанные.')
    
    mark_as_read.short_description = "Отметить как прочитанные"
    
    def mark_as_unread(self, request, queryset):
        """Отметить выбранные сообщения как непрочитанные"""
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} сообщений отмечено как непрочитанные.')
    
    mark_as_unread.short_description = "Отметить как непрочитанные"
    
    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',)
        }


# Регистрация для административной панели статистики
class P2PAdminSite(admin.AdminSite):
    """
    Отдельный административный сайт для P2P модуля
    """
    site_header = 'P2P Биржа - Админ-панель'
    site_title = 'P2P Биржа'
    index_title = 'Администрирование P2P Биржи'


# Дополнительная настройка админки для специального отображения
p2p_admin_site = P2PAdminSite(name='p2p_admin')
p2p_admin_site.register(Order, OrderAdmin)
p2p_admin_site.register(Transaction, TransactionAdmin)
p2p_admin_site.register(Message, MessageAdmin)
