# users/views.py

from django.shortcuts import render, redirect, get_object_or_404
from .models import User
from trees.models import Tree
from referrals.models import Referral, ReferralBonus

def telegram_login(request):
    tg_id = request.GET.get("tg_id")
    if not tg_id:
        return render(request, "users/telegram_login.html")

    try:
        tg_id_int = int(tg_id)
    except ValueError:
        return redirect("home")

    user, created = User.objects.get_or_create(
        telegram_id=tg_id_int,
        defaults={
            "username": "",
            "first_name": "",
            "last_name": "",
            "photo_url": "",
            "cf_balance": 100.00,
            "ton_balance": 0.00
        }
    )

    if created:
        Tree.objects.create(user=user, type="CF")
        user.cf_balance = 100
        user.save()
        ref_code = request.GET.get("ref")
        if ref_code:
            try:
                ref_id_int = int(ref_code)
                referrer = User.objects.filter(telegram_id=ref_id_int).first()
            except (ValueError, User.DoesNotExist):
                referrer = None

            if referrer and referrer != user:
                # *** FAQAT BIR MARTA: user hali referral olmagan bo‘lsa ***
                already_has_ref = Referral.objects.filter(invited=user).exists()
                if not already_has_ref:
                    user.referred_by = referrer
                    user.save()

                    referral = Referral.objects.create(
                        inviter=referrer,
                        invited=user,
                        bonus_cf=10
                    )
                    ReferralBonus.objects.create(
                        referral=referral,
                        bonus_type="signup",
                        amount=10,
                        description=f"Бонус за регистрацию {user}"
                    )
                    referrer.cf_balance += 10
                    referrer.save()
    else:
        if not Tree.objects.filter(user=user).exists():
            Tree.objects.create(user=user, type="CF")

    request.session["telegram_id"] = tg_id_int
    return redirect("home")

def profile_view(request):
    telegram_id = request.session.get("telegram_id") or request.GET.get("telegram_id")
    if not telegram_id:
        return redirect('/telegram_login/')

    user = get_object_or_404(User, telegram_id=telegram_id)

    cf_balance = user.cf_balance
    ton_balance = user.ton_balance
    trees = user.trees.all() if hasattr(user, 'trees') else []
    referral_code = user.referral_code
    photo_url = user.photo_url

    # Referal statistika va ro‘yxat
    direct_referrals = Referral.objects.filter(inviter=user)
    referral_count = direct_referrals.count()
    bonuses = ReferralBonus.objects.filter(referral__inviter=user)
    referral_rewards = sum(b.amount for b in bonuses)
    referrals_info = [{
        'username': r.invited.username,
        'first_name': r.invited.first_name,
        'last_name': r.invited.last_name,
        'joined': r.date_joined,
    } for r in direct_referrals]

    context = {
        "user": user,
        "cf_balance": cf_balance,
        "ton_balance": ton_balance,
        "trees": trees,
        "referral_code": referral_code,
        "photo_url": photo_url,
        "referral_count": referral_count,
        "referral_rewards": referral_rewards,
        "referrals_info": referrals_info,
    }
    return render(request, "users/profile.html", context)
