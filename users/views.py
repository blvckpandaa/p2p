# users/views.py

from django.shortcuts import render, redirect
from .models import User
from trees.models import Tree
from referrals.models import Referral, ReferralBonus

def telegram_login(request):
    """
    1) GET  /telegram_login/               → отдаём HTML с JS, который внутри WebApp
                                           ждет initDataUnsafe.user.id и делает redirect на ?tg_id=…
    2) GET  /telegram_login/?tg_id=123456  → Django создаёт/обновляет User(telegram_id=123456),
                                           кладёт в session["telegram_id"], и делает redirect("home").
    """

    tg_id = request.GET.get("tg_id")
    # 1) Если отсутствует tg_id, показываем «заглушку» (telegram_login.html)
    if not tg_id:
        return render(request, "users/telegram_login.html")

    # 2) Если же есть tg_id в GET – создаём или получаем соответствующего пользователя
    try:
        tg_id_int = int(tg_id)
    except ValueError:
        # Некорректный ID – просто редиректим на главную
        return redirect("home")

    user, created = User.objects.get_or_create(
        telegram_id=tg_id_int,
        defaults={
            "username": "",
            "first_name": "",
            "last_name": "",
            "photo_url": "",
        }
    )

    if created:
        # Если новый пользователь – выдаём ему стартовое дерево
        Tree.objects.create(user=user, type="CF")
        # И обрабатываем реферальный бонус, если был ref-параметр
        ref_code = request.GET.get("ref")
        if ref_code:
            try:
                ref_id_int = int(ref_code)
                referrer = User.objects.filter(telegram_id=ref_id_int).first()
            except (ValueError, User.DoesNotExist):
                referrer = None

            if referrer and referrer != user:
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
        # Если пользователь уже существовал, но у него нет ни одного дерева – создаём старое
        if not Tree.objects.filter(user=user).exists():
            Tree.objects.create(user=user, type="CF")

    # Кладём в сессию telegram_id и перекидываем на home
    request.session["telegram_id"] = tg_id_int
    return redirect("home")
