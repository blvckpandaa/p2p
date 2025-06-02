from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import Staking
from django.utils import timezone
from django.conf import settings

def staking(request):
    """Страница стейкинга"""
    # Проверяем, может ли пользователь использовать стейкинг
    can_access = request.user.can_access_staking()
    
    if not can_access:
        return render(request, 'staking/locked.html', {
            'min_cf': settings.GAME_SETTINGS.get('MIN_CF_FOR_STAKING', 300)
        })
    
    # Получаем активные стейкинги пользователя
    active_stakings = Staking.objects.filter(user=request.user, status='active')
    
    # Получаем завершенные стейкинги, ожидающие получения
    completed_stakings = Staking.objects.filter(user=request.user, status='completed')
    
    # Получаем историю стейкингов
    staking_history = Staking.objects.filter(user=request.user, status='claimed')
    
    return render(request, 'staking/index.html', {
        'active_stakings': active_stakings,
        'completed_stakings': completed_stakings,
        'staking_history': staking_history,
        'user': request.user,
        'staking_bonus': settings.GAME_SETTINGS.get('STAKING_BONUS', 0.1) * 100  # Для отображения в процентах
    })

def create_staking(request):
    """Создание нового стейкинга"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Требуется метод POST'})
    
    # Проверяем, может ли пользователь использовать стейкинг
    if not request.user.can_access_staking():
        return JsonResponse({'status': 'error', 'message': 'Недостаточно CF для стейкинга'})
    
    # Получаем параметры
    amount = request.POST.get('amount')
    token_type = request.POST.get('token_type', 'CF')  # По умолчанию CF
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Некорректная сумма'})
    
    if amount <= 0:
        return JsonResponse({'status': 'error', 'message': 'Сумма должна быть положительной'})
    
    # Проверяем баланс
    if token_type == 'CF' and request.user.cf_balance < amount:
        return JsonResponse({'status': 'error', 'message': 'Недостаточно CF на балансе'})
    
    # Списываем средства
    if token_type == 'CF':
        request.user.cf_balance -= amount
        request.user.save()
    
    # Создаем стейкинг
    staking = Staking(
        user=request.user,
        amount=amount,
        token_type=token_type
    )
    staking.save()  # Дата окончания и награда будут рассчитаны автоматически
    
    return JsonResponse({
        'status': 'success',
        'message': 'Стейкинг успешно создан',
        'staking_id': staking.id,
        'new_balance': request.user.cf_balance if token_type == 'CF' else None
    })

def claim_staking(request, staking_id):
    """Получение награды за стейкинг"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Требуется метод POST'})
    
    # Получаем стейкинг
    staking = get_object_or_404(Staking, id=staking_id, user=request.user)
    
    # Проверяем, что стейкинг завершен
    if staking.status != 'completed':
        return JsonResponse({'status': 'error', 'message': 'Стейкинг еще не завершен'})
    
    # Получаем награду
    success = staking.claim_reward()
    
    if not success:
        return JsonResponse({'status': 'error', 'message': 'Не удалось получить награду'})
    
    return JsonResponse({
        'status': 'success',
        'message': 'Награда успешно получена',
        'new_balance': request.user.cf_balance if staking.token_type == 'CF' else None
    })
