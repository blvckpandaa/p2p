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

def buy_autowater(request, tree_id):
    """Покупка автополива для конкретного дерева"""
    from trees.models import Tree
    from django.views.decorators.csrf import csrf_exempt, csrf_protect
    from django.utils.decorators import method_decorator
    
    # Получаем дерево
    tree = get_object_or_404(Tree, id=tree_id, user=request.user)
    
    # Находим товар автополива
    try:
        item = ShopItem.objects.get(type='auto_water', is_active=True)
    except ShopItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Товар автополив не найден'})
    
    if request.method != 'POST':
        # Если метод GET, просто отображаем страницу подтверждения
        context = {
            'tree': tree,
            'item': item,
            'user': request.user
        }
        return render(request, 'shop/buy_autowater.html', context)
    
    # Если метод POST - выполняем покупку
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
    
    # Устанавливаем автополив для конкретного дерева
    valid_until = timezone.now() + timezone.timedelta(hours=item.duration)
    tree.auto_water_until = valid_until
    tree.save()
    user.save()
    
    # Записываем покупку
    purchase = Purchase.objects.create(
        user=user,
        item=item,
        price_paid=item.price,
        valid_until=valid_until
    )
    
    return JsonResponse({
        'status': 'success',
        'message': f'Вы успешно приобрели автополив для дерева {tree.type}',
        'new_balance': getattr(user, f"{item.price_token_type.lower()}_balance")
    })

def buy_tree(request, tree_type):
    """Покупка дерева определенного типа"""
    if request.method != 'POST':
        # Если метод GET, просто отображаем страницу подтверждения
        context = {
            'tree_type': tree_type,
            'user': request.user
        }
        
        # Если это не CF дерево, находим соответствующий товар
        if tree_type.upper() in ['TON', 'NOT']:
            item_type = f'{tree_type.lower()}_tree'
            try:
                item = ShopItem.objects.get(type=item_type, is_active=True)
                context['item'] = item
            except ShopItem.DoesNotExist:
                pass
        
        return render(request, 'shop/buy_tree.html', context)
    
    # Если метод POST - выполняем покупку
    user = request.user
    
    # Определяем тип дерева и ищем соответствующий товар
    if tree_type.upper() == 'CF':
        # CF дерево выдается бесплатно
        from trees.models import Tree
        if not Tree.objects.filter(user=user, type='CF').exists():
            Tree.objects.create(user=user, type='CF')
        return JsonResponse({
            'status': 'success',
            'message': 'Вы получили дерево CF',
        })
    
    elif tree_type.upper() in ['TON', 'NOT']:
        # Находим товар соответствующего типа
        item_type = f'{tree_type.lower()}_tree'
        try:
            item = ShopItem.objects.get(type=item_type, is_active=True)
        except ShopItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Товар типа {tree_type} не найден'})
        
        # Проверяем, есть ли уже такое дерево
        from trees.models import Tree
        if Tree.objects.filter(user=user, type=tree_type.upper()).exists():
            return JsonResponse({'status': 'error', 'message': f'У вас уже есть дерево {tree_type.upper()}'})
        
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
        
        # Создаем дерево
        Tree.objects.create(user=user, type=tree_type.upper())
        
        # Записываем покупку
        Purchase.objects.create(
            user=user,
            item=item,
            price_paid=item.price
        )
        
        return JsonResponse({
            'status': 'success',
            'message': f'Вы успешно приобрели дерево {tree_type.upper()}',
            'new_balance': getattr(user, f"{item.price_token_type.lower()}_balance")
        })
    
    else:
        return JsonResponse({'status': 'error', 'message': 'Неизвестный тип дерева'})
