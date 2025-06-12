import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
try:
    load_dotenv()
except:
    pass

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "ваш токен")
# Для локальной разработки используйте ngrok или аналогичный сервис
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://b155-185-139-138-17.ngrok-free.app")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", "")

# Проверка обязательных параметров
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
    print("⚠️ Пожалуйста, установите BOT_TOKEN в файле .env или переменных окружения")

# Информация о конфигурации
def print_config_info():
    """Выводит информацию о конфигурации бота"""
    print("\n===== Конфигурация бота =====")
    print(f"Токен бота: {'Установлен' if BOT_TOKEN else 'НЕ УСТАНОВЛЕН'}")
    print(f"URL веб-приложения: {WEBAPP_URL}")
    print(f"ID администратора: {'Установлен' if ADMIN_USER_ID else 'Не установлен'}")
    print("============================\n") 
