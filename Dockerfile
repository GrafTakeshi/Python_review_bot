# Используем официальный образ Python с Alpine (самый легковесный)
FROM python:3.9-alpine

# Устанавливаем системные зависимости
RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    && rm -rf /var/cache/apk/*

# Создаем непривилегированного пользователя
RUN adduser -D appuser && mkdir /app && chown appuser:appuser /app

# Переключаемся на рабочую директорию и пользователя
WORKDIR /app
USER appuser

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Копируем только зависимости сначала (для лучшего кэширования)
COPY --chown=appuser:appuser requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir --user -r requirements.txt

# Копируем остальной код
COPY --chown=appuser:appuser . .

# Точка входа
CMD ["python", "main.py"]