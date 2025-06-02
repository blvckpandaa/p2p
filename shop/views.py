from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import ShopItem, Purchase
from django.utils import timezone

def shop(request):
    """Страница магазина"""
    # Получаем все доступные товары
    items = ShopItem.objects.filter(is_active=True)
    
    return render(request, 'shop/index.html', {
        'items': items,
        'user': request.user
    })

def buy_item(request, item_id):
    """Покупка товара"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Требуется метод POST'})
    
    # Получаем товар
    item = get_object_or_404(ShopItem, id=item_id, is_active=True)
    user = request.user
    
    # Проверяем достаточно ли средств
    if item.price_token_type == 'CF' and user.cf_balance < item.price:
        return JsonResponse({'status': 'error', 'message': 'Недостаточно CF токенов'})
    elif item.price_token_type == 'TON' and user.ton_balance < item.price:
        return JsonResponse({'status': 'error', 'message': 'Недостаточно TON токенов'})
    elif item.price_token_type == 'NOT' and user.not_balance < item.price:
        return JsonResponse({'status': 'error', 'message': 'Недостаточно NOT токенов'})
    
    # Списываем средства
    if item.price_token_type == 'CF':
        user.cf_balance -= item.price
    elif item.price_token_type == 'TON':
        user.ton_balance -= item.price
    elif item.price_token_type == 'NOT':
        user.not_balance -= item.price
    
    user.save()
    
    # Обрабатываем покупку в зависимости от типа товара
    valid_until = None
    
    if item.type == 'auto_water' and item.duration:
        # Авто-полив - устанавливаем время действия
        valid_until = timezone.now() + timezone.timedelta(hours=item.duration)
        user.auto_water_until = valid_until
        user.save()
    
    elif item.type == 'fertilizer' and item.duration:
        # Удобрение - применяем к дереву CF
        from trees.models import Tree
        try:
            tree = Tree.objects.get(user=user, type='CF')
            tree.fertilized_until = timezone.now() + timezone.timedelta(hours=item.duration)
            tree.save()
        except Tree.DoesNotExist:
            pass
    
    elif item.type in ['ton_tree', 'not_tree']:
        # Создаем новое дерево
        from trees.models import Tree
        tree_type = 'TON' if item.type == 'ton_tree' else 'NOT'
        
        # Проверяем, есть ли уже такое дерево
        existing_tree = Tree.objects.filter(user=user, type=tree_type).exists()
        if existing_tree:
            return JsonResponse({'status': 'error', 'message': f'У вас уже есть дерево {tree_type}'})
        
        # Создаем новое дерево
        Tree.objects.create(
            user=user,
            type=tree_type
        )
    
    # Записываем покупку
    purchase = Purchase.objects.create(
        user=user,
        item=item,
        price_paid=item.price,
        valid_until=valid_until
    )
    
    return JsonResponse({
        'status': 'success',
        'message': f'Вы успешно приобрели {item.name}',
        'new_balance': getattr(user, f"{item.price_token_type.lower()}_balance")
    })
