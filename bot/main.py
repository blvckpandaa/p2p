import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters

# Импорт конфигурации
from config import BOT_TOKEN, WEBAPP_URL, ADMIN_USER_ID, print_config_info

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Обработчик команды /start
def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    # Создаем клавиатуру с кнопкой для открытия веб-приложения
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="🌱 Играть", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    # Текст приветствия
    welcome_text = (
        f"Привет, {update.effective_user.first_name}! 👋\n\n"
        "Добро пожаловать в Crypto Farm!\n\n"
        "Нажми на кнопку ниже, чтобы открыть игру:"
    )
    
    update.message.reply_text(welcome_text, reply_markup=keyboard)

# Обработчик команды /help
def help_command(update: Update, context: CallbackContext):
    """Обработчик команды /help"""
    help_text = (
        "Доступные команды:\n"
        "/start - Начать взаимодействие с ботом\n"
        "/help - Показать справку\n"
        "/play - Открыть игру\n"
        "/ref - Получить реферальную ссылку"
    )
    update.message.reply_text(help_text)

# Обработчик команды /play
def play_command(update: Update, context: CallbackContext):
    """Обработчик команды /play"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="🌱 Играть", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    update.message.reply_text("Нажми на кнопку ниже, чтобы открыть игру:", reply_markup=keyboard)

# Обработчик команды /ref
def ref_command(update: Update, context: CallbackContext):
    """Обработчик команды /ref"""
    user_id = update.effective_user.id
    ref_url = f"{WEBAPP_URL}?ref={user_id}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="🔗 Пригласить друзей", url=ref_url)],
        [InlineKeyboardButton(text="🌱 Играть", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    ref_text = (
        f"Ваша реферальная ссылка:\n{ref_url}\n\n"
        f"Поделитесь ею с друзьями, чтобы получить бонусы!"
    )
    
    update.message.reply_text(ref_text, reply_markup=keyboard)

# Обработчик для всех остальных сообщений
def handle_message(update: Update, context: CallbackContext):
    """Обработчик всех остальных сообщений"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="🌱 Играть", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    update.message.reply_text(
        "Используйте /help для списка команд или нажмите кнопку, чтобы открыть игру:",
        reply_markup=keyboard
    )

def main():
    """Запуск бота"""
    # Вывод информации о конфигурации
    print_config_info()
    
    # Создание объекта Updater и передача ему токена бота
    updater = Updater(BOT_TOKEN)
    
    # Получаем диспетчер для регистрации обработчиков
    dispatcher = updater.dispatcher
    
    # Регистрация обработчиков
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("play", play_command))
    dispatcher.add_handler(CommandHandler("ref", ref_command))
    dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    logging.info("Бот запущен!")
    print("✅ Бот успешно запущен и готов к работе!")
    print(f"✨ URL веб-приложения: {WEBAPP_URL}")
    
    updater.start_polling()
    
    # Остановка бота при нажатии Ctrl+C
    updater.idle()

if __name__ == "__main__":
    main() 