# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Speed Up & Slowed Bot
#
# Использует:
#   • Python 3.11-slim как базовый образ
#   • ffmpeg (с поддержкой rubberband для high-quality pitch shift)
#   • Многоэтапная сборка для минимального размера образа
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim AS base

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    librubberband-dev \
    rubberband-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# ── Зависимости Python ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Код приложения ───────────────────────────────────────────────────────────
COPY . .

# Директория для временных файлов
RUN mkdir -p /tmp/audio_bot && chmod 777 /tmp/audio_bot

# ── Переменные окружения ─────────────────────────────────────────────────────
ENV BOT_TOKEN=""
ENV TEMP_DIR="/tmp/audio_bot"
ENV MAX_FILE_SIZE_MB="50"
ENV PROCESSING_TIMEOUT_SEC="120"

# Запуск от непривилегированного пользователя
RUN useradd -m botuser && chown -R botuser:botuser /app /tmp/audio_bot
USER botuser

# ── Healthcheck ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import aiogram; print('OK')" || exit 1

# ── Точка входа ──────────────────────────────────────────────────────────────
CMD ["python", "main.py"]
