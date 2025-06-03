#!/usr/bin/env python
"""Скрипт для обновления балансов пользователей"""
import os
import sys
import django
from decimal import Decimal

# Настраиваем окружение Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cryptofarm.settings")
django.setup()

# Импортируем модель пользователя
from users.models import User

def main():
    """Обновляет баланс CF пользователей"""
    users = User.objects.all()
    
    print(f"Всего пользователей: {users.count()}")
    print("-" * 50)
    
    for user in users:
        # Обновляем баланс только для пользователей с нулевым балансом
        if user.cf_balance == 0:
            old_balance = user.cf_balance
            user.cf_balance = Decimal('100.00')
            user.save()
            
            print(f"Пользователь: {user}")
            print(f"ID: {user.telegram_id}")
            print(f"Старый CF Баланс: {old_balance}")
            print(f"Новый CF Баланс: {user.cf_balance}")
            print("-" * 50)
        else:
            print(f"Пользователь {user} уже имеет ненулевой баланс: {user.cf_balance}")
            print("-" * 50)

if __name__ == "__main__":
    main() 