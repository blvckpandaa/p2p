# D:\oxiri-p2p\bot\bot.py

import os
import sys

# ──────────────────────────────────────────────────────────────────────────────
# 1) Вставляем корень проекта (D:\oxiri-p2p) в sys.path, чтобы Python видел cryptofarm.settings
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ──────────────────────────────────────────────────────────────────────────────
# 2) Указываем Django‐настройки
# ──────────────────────────────────────────────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cryptofarm.settings")

# ──────────────────────────────────────────────────────────────────────────────
# 3) Инициализируем Django (django.setup()), чтобы ORM работал
# ──────────────────────────────────────────────────────────────────────────────
import django
django.setup()

# ──────────────────────────────────────────────────────────────────────────────
# 4) Импортируем модель пользователя
# ──────────────────────────────────────────────────────────────────────────────
from users.models import User as TelegramUser

# ──────────────────────────────────────────────────────────────────────────────
# 5) Подключаем остальные библиотеки для бота
# ──────────────────────────────────────────────────────────────────────────────
import requests
import time
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Импортируем настройки из config.py
from bot.config import BOT_TOKEN, WEBAPP_URL

# Токен вашего бота
TOKEN = BOT_TOKEN
API_URL = f"https://api.telegram.org/bot{TOKEN}"

# URL WebApp (ваш HTTPS‐домен, на котором запущен Django-проектор)
WEBAPP_URL_BASE = f"{WEBAPP_URL}/telegram_login"

last_update_id = 0

def get_updates():
    """
    Получаем обновления от Telegram, используя long polling (getUpdates).
    """
    global last_update_id
    params = {
        "offset": last_update_id + 1,
        "timeout": 30,
        "allowed_updates": ["message", "callback_query"]
    }
    try:
        logger.info(f"Запрашиваю getUpdates с offset={params['offset']}")
        resp = requests.get(f"{API_URL}/getUpdates", params=params, timeout=35)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                results = data.get("result", [])
                if results:
                    last_update_id = results[-1]["update_id"]
                logger.info(f"Получено обновлений: {len(results)}")
                return results
            else:
                logger.error(f"Ошибка API getUpdates: {data}")
        else:
            logger.error(f"HTTP {resp.status_code} на getUpdates: {resp.text}")
    except Exception as e:
        logger.error(f"Исключение при getUpdates: {e}")
    return []

def send_message(chat_id, text, reply_markup=None):
    """
    Отправляем сообщение chat_id с текстом text. Если есть reply_markup — упаковываем его как JSON.
    """
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup)
    try:
        logger.info(f"Отправляю сообщение в чат {chat_id}")
        resp = requests.post(f"{API_URL}/sendMessage", json=params)
        result = resp.json()
        if not result.get("ok"):
            logger.error(f"Ошибка sendMessage: {result}")
        return result
    except Exception as e:
        logger.error(f"Исключение при sendMessage: {e}")
        return {"ok": False, "error": str(e)}

def handle_message(message):
    """
    Обрабатываем текстовые сообщения от пользователя.
    - /start: создаём/обновляем запись в БД и отправляем WebApp‐кнопку.
    - /help: справка.
    - /play: просто шлём ту же WebApp‐кнопку.
    - /ref: выдаём реферальную ссылку (tg_id + ?ref=).
    - иначе: отправляем WebApp‐кнопку.
    """
    chat_id   = message["chat"]["id"]
    text      = message.get("text", "")
    user_info = message.get("from", {})
    telegram_id = user_info.get("id")
    first_name = user_info.get("first_name", "Пользователь")

    logger.info(f"Получено сообщение: {text} от ID={telegram_id} ({first_name})")

    if text == "/start":
        # ────────────────────────────────────────────────────────────────────
        # 5.1) Создаём или обновляем TelegramUser в БД
        # ────────────────────────────────────────────────────────────────────
        try:
            tg_user, created = TelegramUser.objects.get_or_create(
                telegram_id=telegram_id,
                defaults={
                    "username":    user_info.get("username") or "",
                    "first_name":  first_name,
                    "last_name":   user_info.get("last_name") or "",
                    "photo_url":   user_info.get("photo_url") or "",
                    "cf_balance":  0,    # если у модели default=0, можно убрать
                    "ton_balance": 0,    # если у модели default=0, можно убрать
                }
            )
            if not created:
                # Обновляем поля при повторном входе
                tg_user.username   = user_info.get("username") or ""
                tg_user.first_name = first_name
                tg_user.last_name  = user_info.get("last_name") or ""
                tg_user.photo_url  = user_info.get("photo_url") or ""
                tg_user.save()
        except Exception as e:
            logger.error(f"Не удалось создать/обновить User: {e}")

        # ────────────────────────────────────────────────────────────────────
        # 5.2) Формируем WebApp‐URL: https://…/?tg_id=<ID>
        # ────────────────────────────────────────────────────────────────────
        webapp_url = f"{WEBAPP_URL_BASE}?tg_id={telegram_id}"

        welcome_text = (
            f"Привет, {first_name}! 👋\n\n"
            "Ваша учётная запись успешно создана.\n"
            "Нажмите кнопку ниже, чтобы открыть игру."
        )
        webapp_button = {
            "inline_keyboard": [
                [
                    {
                        "text": "🌱 Играть",
                        "web_app": {"url": webapp_url}
                    }
                ]
            ]
        }
        send_message(chat_id, welcome_text, webapp_button)

    elif text == "/help":
        help_text = (
            "Доступные команды:\n"
            "/start — Зарегистрироваться и открыть игру\n"
            "/help  — Показать справку\n"
            "/ref   — Получить реферальную ссылку"
        )
        send_message(chat_id, help_text)

    elif text == "/play":
        # Если пользователь уже зарегистрирован, просто шлём WebApp‐кнопку
        webapp_url = f"{WEBAPP_URL_BASE}?tg_id={telegram_id}"
        play_text = "Нажмите кнопку ниже, чтобы открыть игру:"
        webapp_button = {
            "inline_keyboard": [
                [
                    {
                        "text": "🌱 Играть",
                        "web_app": {"url": webapp_url}
                    }
                ]
            ]
        }
        send_message(chat_id, play_text, webapp_button)

    elif text == "/ref":
        # Формируем реферальную ссылку: /?tg_id=<ID>&ref=<ID>
        ref_url = f"{WEBAPP_URL_BASE}?tg_id={telegram_id}&ref={telegram_id}"
        ref_text = (
            f"Ваша реферальная ссылка:\n{ref_url}\n\n"
            "Поделитесь ею с друзьями, чтобы получить бонусы!"
        )
        ref_buttons = {
            "inline_keyboard": [
                [
                    {"text": "🔗 Пригласить друзей", "url": ref_url}
                ],
                [
                    {
                        "text": "🌱 Играть",
                        "web_app": {"url": ref_url}
                    }
                ]
            ]
        }
        send_message(chat_id, ref_text, ref_buttons)

    else:
        # Любой другой текст — просто показываем WebApp‐кнопку
        webapp_url = f"{WEBAPP_URL_BASE}?tg_id={telegram_id}"
        play_text = "Используйте /help или нажмите кнопку ниже, чтобы открыть игру:"
        webapp_button = {
            "inline_keyboard": [
                [
                    {
                        "text": "🌱 Играть",
                        "web_app": {"url": webapp_url}
                    }
                ]
            ]
        }
        send_message(chat_id, play_text, webapp_button)

if __name__ == "__main__":
    logger.info(f"Запускаем бота. Token={TOKEN[:5]}…, WebApp: {WEBAPP_URL_BASE}")

    # Сбрасываем webhook (если он был настроен)
    try:
        requests.get(f"{API_URL}/deleteWebhook?drop_pending_updates=true")
    except Exception as e:
        logger.error(f"Не удалось сбросить webhook: {e}")

    # Проверяем валидность токена
    try:
        me = requests.get(f"{API_URL}/getMe").json()
        if me.get("ok"):
            logger.info(f"Бот авторизован как @{me['result']['username']}")
        else:
            logger.error(f"Ошибка авторизации бота: {me}")
    except Exception as e:
        logger.error(f"Не удалось проверить токен: {e}")

    # Основной цикл getUpdates
    while True:
        try:
            updates = get_updates()
            for update in updates:
                if "message" in update:
                    handle_message(update["message"])
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Бот остановлен вручную.")
            break
        except Exception as e:
            logger.error(f"Исключение в основном цикле: {e}")
            time.sleep(5)
