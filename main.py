"""
main.py — Точка входа бота.

Запуск:
    python main.py

Переменные окружения:
    BOT_TOKEN           — токен Telegram-бота (обязателен)
    TEMP_DIR            — директория для временных файлов (по умолчанию /tmp/audio_bot)
    MAX_FILE_SIZE_MB    — максимальный размер файла (по умолчанию 50)
    PROCESSING_TIMEOUT_SEC — таймаут обработки (по умолчанию 120)
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN
from bot.handlers import main_router


# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Bot & Dispatcher
# ──────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.critical(
            "❌ BOT_TOKEN не задан! "
            "Укажите его через переменную окружения BOT_TOKEN или в config.py"
        )
        sys.exit(1)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # MemoryStorage — хранит состояния FSM в памяти.
    # Для продакшна замените на RedisStorage:
    #   from aiogram.fsm.storage.redis import RedisStorage
    #   storage = RedisStorage.from_url("redis://localhost:6379")
    storage = MemoryStorage()

    dp = Dispatcher(storage=storage)
    dp.include_router(main_router)

    logger.info("🤖 Бот запускается...")

    # Удаляем webhook (на случай если был установлен ранее)
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        logger.info("🛑 Бот остановлен.")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
