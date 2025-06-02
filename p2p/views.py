from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import Order, Transaction, Message
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db import models
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.urls import reverse

def p2p_market(request):
    """Страница P2P-биржи"""
    # Проверяем, доступна ли биржа пользователю
    if not request.user.can_access_p2p():
        return render(request, 'p2p/locked.html')
    
    # Получаем параметры из запроса
    action = request.GET.get('action', 'buy')
    crypto = request.GET.get('crypto', 'cf')
    
    # Нормализуем crypto
    crypto = crypto.upper()
    
    # Получаем активные ордера для выбранной криптовалюты
    if action == 'buy':
        # Если пользователь хочет купить, показываем ордера на продажу
        orders = Order.objects.filter(type='sell', status='active', token_type=crypto)
        # Исключаем истекшие ордера
        orders = [order for order in orders if not order.is_expired()]
    else:
        # Если пользователь хочет продать, показываем ордера на покупку
        orders = Order.objects.filter(type='buy', status='active', token_type=crypto)
        # Исключаем истекшие ордера
        orders = [order for order in orders if not order.is_expired()]
    
    # Получаем активные транзакции пользователя
    active_deals = Transaction.objects.filter(
        models.Q(buyer=request.user) | models.Q(seller=request.user)
    ).select_related('order').order_by('-created_at')[:5]
    
    # Подготавливаем данные о сделках
    my_deals = []
    for deal in active_deals:
        is_buyer = (deal.buyer == request.user)
        my_deals.append({
            'id': deal.id,
            'order': deal.order,
            'amount': deal.amount,
            'total_price': deal.amount * deal.price_per_unit,
            'is_buyer': is_buyer,
            'created_at': deal.created_at
        })
    
    # Получаем историю транзакций пользователя
    transactions = Transaction.objects.filter(
        models.Q(buyer=request.user) | models.Q(seller=request.user)
    ).select_related('order').order_by('-created_at')
    
    # Пагинация для истории транзакций
    paginator = Paginator(transactions, 10)  # 10 транзакций на страницу
    page = request.GET.get('page')
    
    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        # Если page не является целым числом, выдаем первую страницу
        transactions = paginator.page(1)
    except EmptyPage:
        # Если page больше, чем общее количество страниц, выдаем последнюю
        transactions = paginator.page(paginator.num_pages)
    
    return render(request, 'p2p/index.html', {
        'action': action,
        'crypto': crypto.lower(),
        'orders': orders,
        'my_deals': my_deals,
        'transactions': transactions,
        'user': request.user
    })

def create_order(request):
    """Создание нового ордера"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Требуется метод POST'})
    
    # Проверяем доступ к бирже
    if not request.user.can_access_p2p():
        return JsonResponse({'status': 'error', 'message': 'Доступ к бирже закрыт'})
    
    # Получаем параметры из запроса
    order_type = request.POST.get('type')
    token_type = request.POST.get('token_type', 'CF')  # По умолчанию CF
    amount = request.POST.get('amount')
    price_per_unit = request.POST.get('price')
    min_amount = request.POST.get('min_amount', 100)  # По умолчанию 100
    payment_details = request.POST.get('payment_details', '')
    
    # Валидация
    if not all([order_type, token_type, amount, price_per_unit]):
        return JsonResponse({'status': 'error', 'message': 'Все поля обязательны'})
    
    try:
        amount = float(amount)
        price_per_unit = float(price_per_unit)
        min_amount = float(min_amount)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Некорректный формат чисел'})
    
    if amount <= 0 or price_per_unit <= 0 or min_amount <= 0:
        return JsonResponse({'status': 'error', 'message': 'Значения должны быть положительными'})
    
    # Проверяем баланс для ордера продажи
    if order_type == 'sell':
        balance_field = f"{token_type.lower()}_balance"
        if not hasattr(request.user, balance_field) or getattr(request.user, balance_field) < amount:
            return JsonResponse({'status': 'error', 'message': f'Недостаточно {token_type} на балансе'})
    
    try:
        # Создаем ордер
        order = Order(
            user=request.user,
            type=order_type,
            token_type=token_type,
            amount=amount,
            price_per_unit=price_per_unit,
            min_amount=min_amount,
            payment_details=payment_details
        )
        order.save()  # Дата истечения будет установлена автоматически
        
        # Если это ордер на продажу, блокируем средства
        if order_type == 'sell':
            balance_field = f"{token_type.lower()}_balance"
            setattr(request.user, balance_field, getattr(request.user, balance_field) - amount)
            request.user.save()
            
        # Проверяем, является ли запрос AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Ордер успешно создан',
                'order_id': order.id,
                'redirect_url': None  # Не перенаправляем при AJAX-запросе
            })
        else:
            # Для обычного запроса устанавливаем сообщение и перенаправляем
            messages.success(request, 'Ордер успешно создан')
            return redirect('p2p_market')
            
    except Exception as e:
        # Логируем ошибку
        print(f"Error creating order: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Произошла ошибка при создании ордера: {str(e)}'
        })

@transaction.atomic
def buy_order(request, order_id):
    """Покупка по существующему ордеру"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Требуется метод POST'})
    
    # Проверяем доступ к бирже
    if not request.user.can_access_p2p():
        return JsonResponse({'status': 'error', 'message': 'Доступ к бирже закрыт'})
    
    try:
        # Получаем ордер
        order = get_object_or_404(Order, id=order_id, status='active')
        
        # Нельзя купить свой ордер
        if order.user == request.user:
            return JsonResponse({'status': 'error', 'message': 'Нельзя купить свой ордер'})
        
        # Проверяем, что ордер активен и не истек
        if order.is_expired():
            order.mark_as_expired()
            return JsonResponse({'status': 'error', 'message': 'Ордер истек'})
        
        # Проверяем, достаточно ли средств у покупателя
        total_cost = order.amount * order.price_per_unit
        
        if order.type == 'sell':  # Покупаем токены
            # Проверяем, достаточно ли TON/NOT для покупки CF
            if order.token_type == 'CF':
                payment_token = 'TON'  # Предполагаем, что CF покупается за TON
                if request.user.ton_balance < total_cost:
                    return JsonResponse({'status': 'error', 'message': 'Недостаточно TON для покупки'})
            else:
                payment_token = 'CF'  # TON и NOT покупаются за CF
                if request.user.cf_balance < total_cost:
                    return JsonResponse({'status': 'error', 'message': 'Недостаточно CF для покупки'})
        else:  # Продаем токены (покупаем ордер на покупку)
            # Проверяем, достаточно ли токенов для продажи
            token_balance = getattr(request.user, f"{order.token_type.lower()}_balance")
            if token_balance < order.amount:
                return JsonResponse({'status': 'error', 'message': f'Недостаточно {order.token_type} для продажи'})
            
            payment_token = 'TON' if order.token_type == 'CF' else 'CF'
        
        # Рассчитываем комиссию
        commission_rate = settings.GAME_SETTINGS.get('P2P_COMMISSION', 0.03)
        commission = total_cost * commission_rate
        
        # Выполняем транзакцию
        if order.type == 'sell':  # Покупаем токены
            # Списываем средства у покупателя
            if payment_token == 'TON':
                request.user.ton_balance -= (total_cost + commission)
            else:
                request.user.cf_balance -= (total_cost + commission)
                
            # Начисляем токены покупателю
            setattr(request.user, f"{order.token_type.lower()}_balance", 
                    getattr(request.user, f"{order.token_type.lower()}_balance") + order.amount)
            
            # Начисляем средства продавцу
            if payment_token == 'TON':
                order.user.ton_balance += total_cost
            else:
                order.user.cf_balance += total_cost
        else:  # Продаем токены
            # Списываем токены у продавца
            setattr(request.user, f"{order.token_type.lower()}_balance", 
                    getattr(request.user, f"{order.token_type.lower()}_balance") - order.amount)
            
            # Начисляем средства продавцу
            if payment_token == 'TON':
                request.user.ton_balance += (total_cost - commission)
            else:
                request.user.cf_balance += (total_cost - commission)
                
            # Начисляем токены покупателю
            setattr(order.user, f"{order.token_type.lower()}_balance", 
                    getattr(order.user, f"{order.token_type.lower()}_balance") + order.amount)
        
        # Сохраняем изменения
        request.user.save()
        order.user.save()
        
        # Создаем запись о транзакции
        transaction = Transaction.objects.create(
            order=order,
            buyer=request.user if order.type == 'sell' else order.user,
            seller=order.user if order.type == 'sell' else request.user,
            amount=order.amount,
            price_per_unit=order.price_per_unit,
            token_type=order.token_type,
            commission=commission
        )
        
        # Отмечаем ордер как завершенный
        order.mark_as_completed()
        
        # Проверяем, является ли запрос AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Сделка успешно завершена',
                'transaction_id': transaction.id,
                'redirect_url': reverse('deal_detail', args=[transaction.id])
            })
        else:
            # Для обычного запроса устанавливаем сообщение и перенаправляем
            messages.success(request, 'Сделка успешно завершена')
            return redirect('deal_detail', deal_id=transaction.id)
            
    except Exception as e:
        # Логируем ошибку
        print(f"Error completing order: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Произошла ошибка при выполнении сделки: {str(e)}'
        })

def order_detail(request, order_id):
    """Страница детальной информации о ордере"""
    order = get_object_or_404(Order, id=order_id)
    
    # Проверяем, доступна ли биржа пользователю
    if not request.user.can_access_p2p():
        return render(request, 'p2p/locked.html')
    
    return render(request, 'p2p/order_detail.html', {
        'order': order,
        'user': request.user
    })

def toggle_order(request):
    """Активация/деактивация ордера"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Требуется метод POST'})
    
    order_id = request.POST.get('order_id')
    if not order_id:
        return JsonResponse({'status': 'error', 'message': 'ID ордера не указан'})
    
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Меняем статус
        if order.status == 'active':
            order.status = 'cancelled'
            
            # Возвращаем средства, если это ордер на продажу
            if order.type == 'sell':
                balance_field = f"{order.token_type.lower()}_balance"
                setattr(request.user, balance_field, getattr(request.user, balance_field) + order.amount)
                request.user.save()
        else:
            # Проверяем баланс для ордера продажи при активации
            if order.type == 'sell':
                balance_field = f"{order.token_type.lower()}_balance"
                if not hasattr(request.user, balance_field) or getattr(request.user, balance_field) < order.amount:
                    return JsonResponse({'status': 'error', 'message': f'Недостаточно {order.token_type} на балансе'})
                
                # Блокируем средства снова
                setattr(request.user, balance_field, getattr(request.user, balance_field) - order.amount)
                request.user.save()
            
            order.status = 'active'
            # Обновляем дату истечения
            days = settings.GAME_SETTINGS.get('ORDER_EXPIRY', 3)
            order.expires_at = timezone.now() + timezone.timedelta(days=days)
        
        order.save()
        
        # Формируем сообщение в зависимости от нового статуса
        message = 'Ордер отменен' if order.status == 'cancelled' else 'Ордер активирован'
        
        # Проверяем, является ли запрос AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': message,
                'new_status': order.status
            })
        else:
            # Для обычного запроса устанавливаем сообщение и перенаправляем
            messages.success(request, message)
            return redirect('p2p_market')
            
    except Exception as e:
        # Логируем ошибку
        print(f"Error toggling order: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Произошла ошибка при изменении статуса ордера: {str(e)}'
        })

def deal_detail(request, deal_id):
    """Страница детальной информации о сделке"""
    deal = get_object_or_404(Transaction, id=deal_id)
    
    # Проверяем, является ли пользователь участником сделки
    if request.user != deal.buyer and request.user != deal.seller:
        messages.error(request, 'У вас нет доступа к этой сделке')
        return redirect('p2p_market')
    
    is_buyer = (request.user == deal.buyer)
    
    # Получаем сообщения для этой сделки
    chat_messages = deal.messages.all()
    
    # Отмечаем сообщения как прочитанные
    unread_messages = chat_messages.filter(is_read=False).exclude(sender=request.user)
    for msg in unread_messages:
        msg.is_read = True
        msg.save()
    
    return render(request, 'p2p/deal_detail.html', {
        'deal': deal,
        'is_buyer': is_buyer,
        'user': request.user,
        'chat_messages': chat_messages
    })

def send_message(request, deal_id):
    """Отправка сообщения в чате сделки"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Требуется метод POST'})
    
    deal = get_object_or_404(Transaction, id=deal_id)
    
    # Проверяем, является ли пользователь участником сделки
    if request.user != deal.buyer and request.user != deal.seller:
        return JsonResponse({'status': 'error', 'message': 'У вас нет доступа к этой сделке'})
    
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'status': 'error', 'message': 'Сообщение не может быть пустым'})
    
    try:
        # Создаем сообщение
        message = Message.objects.create(
            transaction=deal,
            sender=request.user,
            content=content
        )
        
        # Проверяем, является ли запрос AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Сообщение отправлено',
                'message_data': {
                    'id': message.id,
                    'content': message.content,
                    'sender_name': str(message.sender),
                    'created_at': message.created_at.strftime('%H:%M, %d.%m.%Y'),
                    'is_my_message': True
                }
            })
        else:
            return redirect('deal_detail', deal_id=deal_id)
            
    except Exception as e:
        # Логируем ошибку
        print(f"Error sending message: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Произошла ошибка при отправке сообщения: {str(e)}'
        })
