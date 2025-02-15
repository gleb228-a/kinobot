import json
from datetime import datetime
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
BOT_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

if not BOT_TOKEN or not ADMIN_ID:
    raise ValueError("Отсутствуют необходимые переменные окружения: ADMIN_BOT_TOKEN или ADMIN_ID")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("ADMIN_ID должен быть числом!")

# Константы для состояний диалога
(
    ADD_TITLE, ADD_YEAR, ADD_DIRECTOR, ADD_GENRE, ADD_PHOTO, ADD_URL, 
    DELETE_ID, ADD_ADMIN_ID, GENERATE_CODE
) = range(9)

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
LOCK_FILE = 'adminbot.lock'

if os.path.exists(LOCK_FILE):
    print("Админ-бот уже запущен. Удалите файл adminbot.lock, если уверены, что другой экземпляр не работает.")
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
            if "admins" not in data:
                data["admins"] = [ADMIN_ID]
            return data
    except FileNotFoundError:
        logger.info("Файл movies.json не найден. Создание нового...")
        return {"movies": [], "admins": [ADMIN_ID]}
    except json.JSONDecodeError:
        logger.error("Ошибка чтения JSON-файла. Файл повреждён или пуст.")
        return {"movies": [], "admins": [ADMIN_ID]}

# Сохранение данных в JSON файл
def save_data(data):
    with open(JSON_FILE, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Проверка прав администратора
def is_admin(user_id):
    data = load_data()
    return user_id in data.setdefault("admins", [])

# Генерация админ-меню с обычными кнопками
def generate_admin_menu():
    keyboard = [
        ["📚 Просмотр базы"],
        ["➕ Добавить фильм"],
        ["🗑️ Удалить фильм"],
        ["👥 Добавить администратора"],
        ["<< Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# Приветствие
async def start(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав на доступ к админ-боту.")
        return

    await update.message.reply_text(
        "🔒 Добро пожаловать в админ-бот!\nЧто вы хотите сделать?",
        reply_markup=generate_admin_menu()
    )

# Обработка текстовых команд
async def handle_admin_command(update: Update, context: CallbackContext):
    command = update.message.text

    if command == "📚 Просмотр базы":
        await admin_view_movies(update, context)
    elif command == "➕ Добавить фильм":
        await admin_add_movie_start(update, context)
    elif command == "🗑️ Удалить фильм":
        await admin_delete_movie_start(update, context)
    elif command == "👥 Добавить администратора":
        await add_admin_start(update, context)
    elif command == "<< Назад":
        await show_admin_menu(update, context)
    else:
        logger.warning(f"Неизвестная команда: {command}")
        await update.message.reply_text("❌ Неизвестная команда.", reply_markup=generate_admin_menu())

# Возврат в админ-меню
async def show_admin_menu(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🔒 Админ-меню:\nЧто вы хотите сделать дальше?",
        reply_markup=generate_admin_menu()
    )

# Команда: Просмотр базы фильмов
async def admin_view_movies(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав на доступ к этой команде.")
        return

    data = load_data()
    movies = data.setdefault("movies", [])

    if not movies:
        await update.message.reply_text("❌ База фильмов пуста.", reply_markup=generate_admin_menu())
        return

    response = "📚 Список фильмов:\n\n"
    for movie in movies:
        response += (
            f"ID: {movie['id']} | Код: {movie.get('code', 'Нет кода')} | Название: {movie['title']} | Год: {movie['year']} | "
            f"Режиссер: {movie['director']} | Жанр: {', '.join(movie['genre'])}\n"
        )

    await update.message.reply_text(response, reply_markup=generate_admin_menu())

# Команда: Начало добавления нового фильма
async def admin_add_movie_start(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав на доступ к этой команде.")
        return ConversationHandler.END

    await update.message.reply_text("🎥 Введите название фильма:", reply_markup=ReplyKeyboardMarkup([["<< Назад"]], resize_keyboard=True))
    return ADD_TITLE

# Добавление названия фильма
async def admin_add_title(update: Update, context: CallbackContext):
    title = update.message.text.strip()
    if title.lower() == "<< назад":
        await show_admin_menu(update, context)
        return ConversationHandler.END

    context.user_data['title'] = title
    await update.message.reply_text("🗓️ Введите год выпуска фильма:")
    return ADD_YEAR

# Добавление года выпуска фильма
async def admin_add_year(update: Update, context: CallbackContext):
    try:
        year = int(update.message.text.strip())
        if year < 1800 or year > datetime.now().year:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректный год (число от 1800 до текущего года).")
        return ADD_YEAR

    context.user_data['year'] = year
    await update.message.reply_text("👨‍🎤 Введите режиссера фильма:")
    return ADD_DIRECTOR

# Добавление режиссера фильма
async def admin_add_director(update: Update, context: CallbackContext):
    director = update.message.text.strip()
    if director.lower() == "<< назад":
        await show_admin_menu(update, context)
        return ConversationHandler.END

    context.user_data['director'] = director
    await update.message.reply_text("🎭 Введите жанры фильма (через запятую):")
    return ADD_GENRE

# Добавление жанров фильма
async def admin_add_genre(update: Update, context: CallbackContext):
    genres = [genre.strip() for genre in update.message.text.split(',')]
    if update.message.text.lower() == "<< назад":
        await show_admin_menu(update, context)
        return ConversationHandler.END

    context.user_data['genre'] = genres
    await update.message.reply_text("🖼️ Отправьте фото фильма (если есть):", reply_markup=ReplyKeyboardMarkup([["<< Пропустить"]], resize_keyboard=True))
    return ADD_PHOTO

# Добавление фото фильма
async def admin_add_photo(update: Update, context: CallbackContext):
    if update.message.photo:
        photo_url = update.message.photo[-1].file_id
        try:
            # Проверяем, что фото действительное
            file_info = await context.bot.get_file(photo_url)
            context.user_data['photo_url'] = photo_url
            await update.message.reply_text("🔗 Введите ссылку для просмотра фильма:")
        except Exception as e:
            logger.error(f"Ошибка при загрузке фото: {e}")
            await update.message.reply_text("❌ Недействительное фото. Пожалуйста, отправьте другое изображение или пропустите этот шаг.")
            return ADD_PHOTO
    elif update.message.text == "<< Пропустить":
        context.user_data['photo_url'] = ""
        await update.message.reply_text("🔗 Введите ссылку для просмотра фильма:")
    else:
        await update.message.reply_text("❌ Пожалуйста, отправьте фото или нажмите << Пропустить.")
        return ADD_PHOTO

    return ADD_URL

# Добавление ссылки для просмотра фильма
async def admin_add_url(update: Update, context: CallbackContext):
    watch_url = update.message.text.strip()
    if watch_url.lower() == "<< назад":
        await show_admin_menu(update, context)
        return ConversationHandler.END

    context.user_data['watch_url'] = watch_url

    # Генерация уникального кода фильма
    unique_code = generate_movie_code()
    context.user_data['code'] = unique_code

    # Генерация нового ID
    data = load_data()
    movies = data.setdefault("movies", [])
    new_id = str(len(movies) + 1).zfill(3)

    # Создание фильма
    new_movie = {
        "id": new_id,
        "code": unique_code,
        "title": context.user_data['title'],
        "year": context.user_data['year'],
        "director": context.user_data['director'],
        "genre": context.user_data['genre'],
        "photo_url": context.user_data.get('photo_url', ""),
        "watch_url": context.user_data['watch_url'],
        "added_date": datetime.now().strftime('%Y-%m-%d'),
        "ratings": [],
        "reviews": []
    }
    movies.append(new_movie)
    save_data(data)

    await update.message.reply_text(
        f"🎉 Фильм успешно добавлен!\n\n"
        f"🎬 *ID*: {new_id}\n"
        f"🎞️ *Код*: `{unique_code}`\n"
        f"🎥 *Название*: {new_movie['title']}\n"
        f"🗓️ *Год*: {new_movie['year']}\n"
        f"👨‍🎤 *Режиссер*: {new_movie['director']}\n"
        f"🎭 *Жанр*: {', '.join(new_movie['genre'])}\n"
        f"🔗 [Смотреть фильм]({new_movie.get('watch_url', '')})",
        parse_mode="Markdown",
        reply_markup=generate_admin_menu()
    )
    return ConversationHandler.END

# Генерация уникального кода фильма
def generate_movie_code():
    import random
    import string
    code_length = 6
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=code_length))

# Команда: Начало удаления фильма
async def admin_delete_movie_start(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав на доступ к этой команде.")
        return ConversationHandler.END

    await update.message.reply_text("🗑️ Введите ID фильма для удаления:", reply_markup=ReplyKeyboardMarkup([["<< Назад"]], resize_keyboard=True))
    return DELETE_ID

# Подтверждение удаления фильма
async def admin_confirm_delete(update: Update, context: CallbackContext):
    movie_id = update.message.text.strip()
    if movie_id.lower() == "<< назад":
        await show_admin_menu(update, context)
        return ConversationHandler.END

    data = load_data()
    movies = data.setdefault("movies", [])
    movie = next((m for m in movies if m['id'] == movie_id), None)

    if not movie:
        await update.message.reply_text(f"❌ Фильм с ID {movie_id} не найден.", reply_markup=generate_admin_menu())
        return ConversationHandler.END

    movies = [m for m in movies if m['id'] != movie_id]
    save_data(data)

    await update.message.reply_text(f"✅ Фильм с ID {movie_id} успешно удален.", reply_markup=generate_admin_menu())
    return ConversationHandler.END

# Команда: Добавление нового администратора
async def add_admin_start(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав на доступ к этой команде.")
        return ConversationHandler.END

    await update.message.reply_text("👥 Введите Telegram ID нового администратора:", reply_markup=ReplyKeyboardMarkup([["<< Назад"]], resize_keyboard=True))
    return ADD_ADMIN_ID

# Подтверждение добавления администратора
async def confirm_add_admin(update: Update, context: CallbackContext):
    admin_id = update.message.text.strip()
    if admin_id.lower() == "<< назад":
        await show_admin_menu(update, context)
        return ConversationHandler.END

    try:
        admin_id = int(admin_id)
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректный ID (число).", reply_markup=generate_admin_menu())
        return ADD_ADMIN_ID

    data = load_data()
    admins = data.setdefault("admins", [])
    if admin_id in admins:
        await update.message.reply_text(f"❌ Пользователь с ID {admin_id} уже является администратором.", reply_markup=generate_admin_menu())
        return ConversationHandler.END

    admins.append(admin_id)
    data["admins"] = admins
    save_data(data)

    await update.message.reply_text(f"✅ Пользователь с ID {admin_id} успешно добавлен как администратор.", reply_markup=generate_admin_menu())
    return ConversationHandler.END

# Отмена операции
async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text(" OPERATION CANCELLED.", reply_markup=generate_admin_menu())
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
    WEBHOOK_URL = f"https://YOUR_RAILWAY_APP_URL/adminbot"
    await application.bot.set_webhook(url=WEBHOOK_URL)

    # Запуск бота через webhook
    logger.info("Админ-бот запущен!")
    await application.start()
    await application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv('PORT', 8080)),  # Использует порт из переменных окружения Railway
        url_path="adminbot",
        webhook_url=WEBHOOK_URL
    )

    # Настройка обработчиков
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📚 Просмотр базы$"), admin_view_movies),
            MessageHandler(filters.Regex("^➕ Добавить фильм$"), admin_add_movie_start),
            MessageHandler(filters.Regex("^🗑️ Удалить фильм$"), admin_delete_movie_start),
            MessageHandler(filters.Regex("^👥 Добавить администратора$"), add_admin_start)
        ],
        states={
            ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_title)],
            ADD_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_year)],
            ADD_DIRECTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_director)],
            ADD_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_genre)],
            ADD_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT, admin_add_photo)],
            ADD_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_url)],
            DELETE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_confirm_delete)],
            ADD_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_add_admin)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("<< Назад"), show_admin_menu)
        ]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    # Запуск бота через webhook
    logger.info("Админ-бот запущен!")
    await application.run_webhook(
        listen="0.0.0.0",
        port=8080,
        url_path="adminbot",
        webhook_url=f"https://YOUR_RAILWAY_APP_URL/adminbot"
    )

  # Функция для обработки входящих обновлений
async def process_update(update_data):
    application = Application.builder().token(BOT_TOKEN).build()
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)