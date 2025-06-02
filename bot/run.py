#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота CryptoFarm с использованием python-telegram-bot
"""

if __name__ == "__main__":
    from main import main
    
    print("🤖 Запускаем бота CryptoFarm (python-telegram-bot)...")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при запуске бота: {e}") 