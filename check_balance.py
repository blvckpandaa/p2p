#!/usr/bin/env python
"""Скрипт для проверки баланса пользователей"""
import os
import sys
import django

# Настраиваем окружение Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cryptofarm.settings")
django.setup()

# Импортируем модель пользователя
from users.models import User

def main():
    """Выводит информацию о балансах пользователей"""
    users = User.objects.all()
    
    print(f"Всего пользователей: {users.count()}")
    print("-" * 50)
    
    for user in users:
        print(f"Пользователь: {user}")
        print(f"ID: {user.telegram_id}")
        print(f"CF Баланс: {user.cf_balance}")
        print(f"TON Баланс: {user.ton_balance}")
        print("-" * 50)

if __name__ == "__main__":
    main() 