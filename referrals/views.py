from django.shortcuts import render
from .models import Referral, ReferralBonus
from django.db import models

def referral_program(request):
    user = request.user
    direct_referrals = Referral.objects.filter(inviter=user)
    referral_count = direct_referrals.count()
    bonuses = ReferralBonus.objects.filter(referral__inviter=user)
    referral_rewards = sum(b.amount for b in bonuses)

    next_bonus_step = 5
    next_badge = ((referral_count // next_bonus_step) + 1) * next_bonus_step
    referal_to_next_badge = max(0, next_badge - referral_count)

    main_stats = f"Вы пригласили <b>{referral_count}</b> друзей и заработали <b>{referral_rewards} CF</b>!"
    if referal_to_next_badge == 0:
        motivation_text = "Поздравляем! Вы получили новый бейдж или бонус! 🏅"
    else:
        motivation_text = f"Пригласите ещё <b>{referal_to_next_badge}</b> друзей — получите <b>50 CF бонус</b> и новый бейдж! 🚀"

    bot_username = "p2pFloriya_bot"
    referral_link = f"https://t.me/{bot_username}?start={user.referral_code}"

    context = {
        'referral_count': referral_count,
        'referral_rewards': referral_rewards,
        'main_stats': main_stats,
        'motivation_text': motivation_text,
        'referral_link': referral_link,
        'user': user,
    }
    return render(request, 'referral/index.html', context)


