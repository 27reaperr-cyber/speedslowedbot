"""
handlers/common.py — /start, /help и прочие базовые команды.
"""

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router(name="common")

WELCOME_TEXT = """
🎧 <b>Speed Up & Slowed Bot</b>

Привет! Я умею обрабатывать аудиофайлы:

🚀 <b>Speed Up</b> — ускорить (1.25×, 1.5×, 2×)
🐌 <b>Slowed</b>   — замедлить (0.75×, 0.5×)
🎵 <b>Pitch</b>    — изменить тональность (±1, ±2 полутона)
🎚 <b>Custom</b>   — любая скорость от 0.25 до 4.0

<b>Как пользоваться:</b>
1. Отправь мне аудиофайл или голосовое сообщение
2. Выбери действие в меню
3. Получи обработанный файл ✨

<b>Поддерживаемые форматы:</b>
mp3, wav, ogg, m4a, flac, aac, opus, wma, aiff

<b>Максимальный размер:</b> 50 МБ
"""


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(WELCOME_TEXT, parse_mode="HTML")
