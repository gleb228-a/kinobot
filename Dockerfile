# Основной образ Python
FROM python:3.10

# Установка рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY . .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Запуск Flask-сервера
CMD ["python", "server.py"]