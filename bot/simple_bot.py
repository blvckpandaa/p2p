#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Настраиваем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = "ваш токен"

# URL веб-приложения
WEBAPP_URL = "http://localhost:8000"

# Определяем функции-обработчики
def start(update, context):
    """Обработчик команды /start."""
    user = update.effective_user
    update.message.reply_text(
        f'Привет, {user.first_name}! Я бот для CryptoFarm.\n'
        f'Нажми /help для получения списка команд.'
    )

def help_command(update, context):
    """Обработчик команды /help."""
    update.message.reply_text(
        'Доступные команды:\n'
        '/start - Начать взаимодействие с ботом\n'
        '/help - Показать справку\n'
        '/webapp - Открыть веб-приложение\n'
        '/ref - Получить реферальную ссылку'
    )

def webapp_command(update, context):
    """Обработчик команды /webapp."""
    update.message.reply_text(
        f'Для доступа к веб-приложению перейдите по ссылке:\n{WEBAPP_URL}'
    )

def ref_command(update, context):
    """Обработчик команды /ref."""
    user_id = update.effective_user.id
    ref_url = f"{WEBAPP_URL}?ref={user_id}"
    update.message.reply_text(
        f'Ваша реферальная ссылка:\n{ref_url}\n\n'
        f'Поделитесь ею с друзьями, чтобы получить бонусы!'
    )

def echo(update, context):
    """Обработчик текстовых сообщений."""
    update.message.reply_text(
        'Я получил ваше сообщение. Используйте /help для списка команд.'
    )

def error(update, context):
    """Обработчик ошибок."""
    logger.warning('Update "%s" вызвал ошибку "%s"', update, context.error)

def main():
    """Запускаем бота."""
    print("🤖 Запускаем бота CryptoFarm...")
    
    # Создаем объект Updater и передаем ему токен
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("webapp", webapp_command))
    dp.add_handler(CommandHandler("ref", ref_command))

    # Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Регистрируем обработчик ошибок
    dp.add_error_handler(error)

    # Запускаем бота
    updater.start_polling()
    print("✅ Бот успешно запущен и готов к работе!")
    print(f"✨ URL веб-приложения: {WEBAPP_URL}")

    # Останавливаем бота при нажатии Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main() 
