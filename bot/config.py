"""
config.py — Конфигурация бота.
Читает переменные окружения, задаёт глобальные константы.
"""

import os
from pathlib import Path

# ──────────────────────────────────────────────
# Telegram
# ──────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ──────────────────────────────────────────────
# Файловая система
# ──────────────────────────────────────────────
TEMP_DIR: Path = Path(os.getenv("TEMP_DIR", "/tmp/audio_bot"))
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# Ограничения
# ──────────────────────────────────────────────
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

PROCESSING_TIMEOUT_SEC: int = int(os.getenv("PROCESSING_TIMEOUT_SEC", "120"))

# ──────────────────────────────────────────────
# Поддерживаемые форматы
# ──────────────────────────────────────────────
SUPPORTED_AUDIO_EXTENSIONS: set[str] = {
    ".mp3", ".wav", ".ogg", ".m4a", ".flac",
    ".aac", ".opus", ".wma", ".aiff",
}

SUPPORTED_MIME_TYPES: set[str] = {
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4",
    "audio/flac", "audio/aac", "audio/opus", "audio/x-ms-wma",
    "audio/aiff", "audio/x-wav", "audio/x-flac",
    "audio/x-m4a", "video/mp4",  # некоторые клиенты шлют m4a как video/mp4
}

# ──────────────────────────────────────────────
# Допустимые диапазоны скорости и питча
# ──────────────────────────────────────────────
MIN_SPEED: float = 0.25
MAX_SPEED: float = 4.0

MIN_PITCH_SEMITONES: int = -12
MAX_PITCH_SEMITONES: int = 12
