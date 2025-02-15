import asyncio
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

# Импортируем функции main из обоих ботов
from cinemabot import main as cinemabot_main
from adminbot import main as adminbot_main

async def run_bots():
    # Запускаем основной бот
    asyncio.create_task(cinemabot_main())

    # Запускаем админ-бот
    asyncio.create_task(adminbot_main())

    # Ждём завершения задач
    await asyncio.gather(cinemabot_main(), adminbot_main())

if __name__ == '__main__':
    try:
        asyncio.run(run_bots())
    except KeyboardInterrupt:
        print("Боты остановлены.")