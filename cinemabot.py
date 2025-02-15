import json
from dotenv import load_dotenv
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackContext,
)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('MAIN_BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("Отсутствует переменная окружения MAIN_BOT_TOKEN")

# Константы для состояний диалога
FIND_ID = range(1)

# Путь к JSON файлу
JSON_FILE = 'movies.json'

# Логирование
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Проверка наличия lock-файла
LOCK_FILE = 'cinemabot.lock'

if os.path.exists(LOCK_FILE):
    print("Основной бот уже запущен. Удалите файл cinemabot.lock, если уверены, что другой экземпляр не работает.")
    exit()

with open(LOCK_FILE, 'w') as f:
    f.write(str(os.getpid()))

def cleanup_lock_file():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

import atexit
atexit.register(cleanup_lock_file)  # Удаляем lock-файл при завершении работы бота


# Загрузка данных из JSON файла
def load_data():
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if "movies" not in data:
                data["movies"] = []
            return data
    except FileNotFoundError:
        logger.info("Файл movies.json не найден. Создание нового...")
        return {"movies": []}
    except json.JSONDecodeError:
        logger.error("Ошибка чтения JSON-файла. Файл повреждён или пуст.")
        return {"movies": []}

# Получение фильма по ID
def get_movie_by_id(movies, movie_id):
    return next((movie for movie in movies if movie['id'] == movie_id), None)

# Генерация главного меню с обычными кнопками
def generate_main_menu():
    keyboard = [
        ["🎬 Найти фильм"],
        ["<< Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# Приветствие
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "👋 Добро пожаловать в *КиноБот*! 🎥\n"
        "Здесь вы можете находить фильмы по их ID.\n\n"
        "Что вы хотите сделать?",
        parse_mode="Markdown",
        reply_markup=generate_main_menu()
    )

# Обработка текстовых команд
async def handle_command(update: Update, context: CallbackContext):
    command = update.message.text

    if command == "🎬 Найти фильм":
        await find_movie_start(update, context)
    elif command == "<< Назад":
        await show_main_menu(update, context)
    else:
        logger.warning(f"Неизвестная команда: {command}")
        await update.message.reply_text("❌ Неизвестная команда.", reply_markup=generate_main_menu())

# Возврат в главное меню
async def show_main_menu(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🤖 Главное меню:\nЧто вы хотите сделать дальше?",
        reply_markup=generate_main_menu()
    )

# Поиск фильма
async def find_movie_start(update: Update, context: CallbackContext):
    await update.message.reply_text("🔍 Введите ID фильма для поиска:", reply_markup=ReplyKeyboardMarkup([["<< Назад"]], resize_keyboard=True))
    return FIND_ID

async def find_movie(update: Update, context: CallbackContext):
    movie_id = update.message.text.strip()
    if movie_id.lower() == "<< назад":
        await show_main_menu(update, context)
        return ConversationHandler.END

    data = load_data()
    movies = data.setdefault("movies", [])  # Защита от KeyError
    movie = get_movie_by_id(movies, movie_id)

    if not movie:
        await update.message.reply_text(
            f"❌ Фильм с ID {movie_id} не найден.",
            reply_markup=generate_main_menu()
        )
        return ConversationHandler.END

    response = (
        f"🎥 *Название*: {movie['title']}\n"
        f"🗓️ *Год*: {movie['year']}\n"
        f"👨‍🎤 *Режиссер*: {movie['director']}\n"
        f"🎭 *Жанр*: {', '.join(movie['genre'])}\n"
        f"🔗 [Смотреть фильм]({movie.get('watch_url', '')})\n"
    )

    if movie.get("photo_url"):
        try:
            await update.message.reply_photo(
                photo=movie["photo_url"],
                caption=response,
                parse_mode="Markdown",
                reply_markup=generate_main_menu()
            )
        except Exception as e:
            logger.warning(f"Ошибка при отправке фото: {e}")
            await update.message.reply_text(
                f"⚠️ Для этого фильма недоступно изображение.\n{response}",
                parse_mode="Markdown",
                reply_markup=generate_main_menu()
            )
    else:
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            reply_markup=generate_main_menu()
        )

    return ConversationHandler.END

# Отмена операции
async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text(" OPERATION CANCELLED.", reply_markup=generate_main_menu())
    return ConversationHandler.END

# Функция для обработки входящих обновлений
async def process_update(update_data):
    application = Application.builder().token(BOT_TOKEN).build()
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)

# Основная функция
async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Удаляем старый webhook
    await application.bot.delete_webhook()

    # Устанавливаем новый webhook
    WEBHOOK_URL = f"https://YOUR_RAILWAY_APP_URL/cinemabot"
    await application.bot.set_webhook(url=WEBHOOK_URL)

    # Запуск бота через webhook
    logger.info("Основной бот запущен!")
    await application.start()
    await application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv('PORT', 8080)),  # Использует порт из переменных окружения Railway
        url_path="cinemabot",
        webhook_url=WEBHOOK_URL
    )

    # Настройка обработчиков
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🎬 Найти фильм$"), find_movie_start)],
        states={
            FIND_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, find_movie)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("<< Назад"), show_main_menu)
        ]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)



    # Запуск бота через webhook
    logger.info("Основной бот запущен!")
    await application.run_webhook(
        listen="0.0.0.0",
        port=8080,
        url_path="cinemabot",
        webhook_url=f"https://YOUR_RAILWAY_APP_URL/cinemabot"
    )
    

 # Функция для обработки входящих обновлений
async def process_update(update_data):
    application = Application.builder().token(BOT_TOKEN).build()
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)