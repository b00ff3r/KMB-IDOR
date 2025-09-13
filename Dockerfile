# Используем минимальный образ Python
FROM python:3.11-slim

# Установим рабочую директорию
WORKDIR /app

# Установим зависимости системы (для pip и компиляции, если нужно)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Скопируем файлы приложения
COPY . /app

# Установим зависимости Python (у тебя только Flask)
RUN pip install --no-cache-dir flask

# Откроем порт
EXPOSE 5000

# Запустим приложение
CMD ["python", "app.py"]
