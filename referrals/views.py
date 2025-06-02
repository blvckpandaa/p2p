from django.shortcuts import render
from django.http import JsonResponse
from .models import Referral, ReferralBonus

def referral_program(request):
    """Страница реферальной программы"""
    # Получаем всех рефералов пользователя
    referrals = Referral.objects.filter(inviter=request.user)
    
    # Получаем бонусы пользователя
    bonuses = ReferralBonus.objects.filter(referral__inviter=request.user)
    
    # Общий заработок с рефералов
    total_earnings = sum(bonus.amount for bonus in bonuses)
    
    # Генерируем реферальную ссылку
    referral_link = f"https://t.me/{request.get_host()}?ref={request.user.referral_code}"
    
    return render(request, 'referral/index.html', {
        'referrals': referrals,
        'bonuses': bonuses,
        'total_earnings': total_earnings,
        'referral_link': referral_link,
        'user': request.user
    })
