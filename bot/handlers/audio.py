"""
handlers/audio.py — Обработка аудиофайлов и inline-кнопок.

Состояния FSM:
  WaitingForAction  — файл получен, ждём выбора из меню
  WaitingForSpeed   — ждём ввода пользовательской скорости

Хранилище состояния использует MemoryStorage (можно заменить на Redis).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Audio,
    CallbackQuery,
    Document,
    FSInputFile,
    Message,
    Voice,
)

from bot.config import (
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_AUDIO_EXTENSIONS,
    SUPPORTED_MIME_TYPES,
    TEMP_DIR,
    MIN_SPEED,
    MAX_SPEED,
    MIN_PITCH_SEMITONES,
    MAX_PITCH_SEMITONES,
)
from bot.keyboards import back_only, cancel_only, main_menu
from bot.services import change_pitch, change_speed, cleanup

logger = logging.getLogger(__name__)
router = Router(name="audio")


# ──────────────────────────────────────────────────────────────────────────────
# FSM States
# ──────────────────────────────────────────────────────────────────────────────

class AudioStates(StatesGroup):
    waiting_for_action = State()   # файл загружен, меню показано
    waiting_for_speed  = State()   # ждём ввода числа (custom speed)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _is_supported_mime(mime: Optional[str]) -> bool:
    if not mime:
        return True  # не паникуем, если mime не пришёл
    return mime in SUPPORTED_MIME_TYPES or mime.startswith("audio/")


def _is_supported_ext(filename: Optional[str]) -> bool:
    if not filename:
        return True
    return Path(filename).suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS


async def _download_to_temp(bot: Bot, file_id: str, original_name: str = "audio.mp3") -> Path:
    """Скачивает файл из Telegram во временную директорию."""
    suffix = Path(original_name).suffix or ".mp3"
    dest = TEMP_DIR / f"{file_id}{suffix}"
    if not dest.exists():
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination=str(dest))
    return dest


async def _send_result(
    message: Message,
    output_path: Path,
    caption: str,
    input_path: Optional[Path] = None,
) -> None:
    """Отправляет результат и чистит временные файлы."""
    try:
        audio_file = FSInputFile(str(output_path), filename=output_path.name)
        await message.answer_audio(audio_file, caption=caption)
    finally:
        cleanup(output_path, input_path)


def _show_main_menu_text(filename: str) -> str:
    return (
        f"🎵 <b>{filename}</b>\n\n"
        "Выберите действие:"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Receive audio
# ──────────────────────────────────────────────────────────────────────────────

async def _handle_any_audio(
    message: Message,
    state: FSMContext,
    file_id: str,
    file_size: Optional[int],
    filename: str,
    mime_type: Optional[str],
) -> None:
    """Общая логика для Audio, Document, Voice."""
    # Проверка размера
    if file_size and file_size > MAX_FILE_SIZE_BYTES:
        await message.answer(
            f"❌ Файл слишком большой: <b>{file_size / 1_048_576:.1f} МБ</b>.\n"
            f"Максимум — <b>50 МБ</b>.",
            parse_mode="HTML",
        )
        return

    # Проверка формата
    if not (_is_supported_mime(mime_type) or _is_supported_ext(filename)):
        await message.answer(
            "❌ Неподдерживаемый формат файла.\n"
            "Поддерживаются: mp3, wav, ogg, m4a, flac, aac, opus, wma, aiff."
        )
        return

    # Сохраняем данные в FSM
    await state.set_state(AudioStates.waiting_for_action)
    await state.update_data(
        file_id=file_id,
        filename=filename,
        mime_type=mime_type,
    )

    await message.answer(
        _show_main_menu_text(filename),
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


@router.message(F.audio)
async def handle_audio(message: Message, state: FSMContext) -> None:
    audio: Audio = message.audio
    await _handle_any_audio(
        message, state,
        file_id=audio.file_id,
        file_size=audio.file_size,
        filename=audio.file_name or "audio.mp3",
        mime_type=audio.mime_type,
    )


@router.message(F.voice)
async def handle_voice(message: Message, state: FSMContext) -> None:
    voice: Voice = message.voice
    await _handle_any_audio(
        message, state,
        file_id=voice.file_id,
        file_size=voice.file_size,
        filename="voice.ogg",
        mime_type=voice.mime_type or "audio/ogg",
    )


@router.message(F.document)
async def handle_document(message: Message, state: FSMContext) -> None:
    doc: Document = message.document
    filename = doc.file_name or "audio.mp3"
    mime = doc.mime_type or ""

    # Проверяем что документ — аудио
    if not (_is_supported_mime(mime) or _is_supported_ext(filename)):
        await message.answer(
            "❌ Файл не распознан как аудио.\n"
            "Отправь mp3, wav, ogg, m4a, flac или другой аудиоформат."
        )
        return

    await _handle_any_audio(
        message, state,
        file_id=doc.file_id,
        file_size=doc.file_size,
        filename=filename,
        mime_type=mime,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Callback handlers
# ──────────────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("section:"))
async def cb_section_header(call: CallbackQuery) -> None:
    """Нажатие на заголовок секции — просто убираем уведомление."""
    await call.answer()


@router.callback_query(F.data == "cancel:")
async def cb_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("❌ Отменено. Отправьте новый аудиофайл.")
    await call.answer()


@router.callback_query(F.data == "back:")
async def cb_back(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    filename = data.get("filename", "audio")
    await call.message.edit_text(
        _show_main_menu_text(filename),
        reply_markup=main_menu(),
        parse_mode="HTML",
    )
    await call.answer()


# ── Speed ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("speed:"), AudioStates.waiting_for_action)
async def cb_speed(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await call.answer("⏳ Обрабатываю...")

    speed = float(call.data.split(":")[1])
    data  = await state.get_data()

    await call.message.edit_text(
        f"⏳ Изменяю скорость <b>{speed}×</b>...",
        parse_mode="HTML",
    )

    input_path: Optional[Path] = None
    output_path: Optional[Path] = None

    try:
        input_path  = await _download_to_temp(bot, data["file_id"], data["filename"])
        output_path = await change_speed(input_path, speed)

        label = f"{'🚀 Speed Up' if speed > 1 else '🐌 Slowed'} {speed}×"
        await _send_result(
            call.message,
            output_path,
            caption=f"✅ {label}\n📁 {data['filename']}",
            input_path=input_path,
        )
        output_path = None  # уже удалён внутри _send_result

    except RuntimeError as e:
        logger.error("Speed processing error: %s", e)
        await call.message.answer(f"❌ Ошибка обработки: {e}")
    finally:
        cleanup(output_path)

    await state.clear()


# ── Pitch ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pitch:"), AudioStates.waiting_for_action)
async def cb_pitch(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await call.answer("⏳ Обрабатываю...")

    semitones = int(call.data.split(":")[1])
    data      = await state.get_data()

    sign  = "+" if semitones > 0 else ""
    label = f"🎵 Pitch {sign}{semitones} st"

    await call.message.edit_text(
        f"⏳ Сдвигаю тональность <b>{sign}{semitones} полутонов</b>...",
        parse_mode="HTML",
    )

    input_path: Optional[Path]  = None
    output_path: Optional[Path] = None

    try:
        input_path  = await _download_to_temp(bot, data["file_id"], data["filename"])
        output_path = await change_pitch(input_path, semitones)

        await _send_result(
            call.message,
            output_path,
            caption=f"✅ {label}\n📁 {data['filename']}",
            input_path=input_path,
        )
        output_path = None

    except RuntimeError as e:
        logger.error("Pitch processing error: %s", e)
        await call.message.answer(f"❌ Ошибка обработки: {e}")
    finally:
        cleanup(output_path)

    await state.clear()


# ── Custom speed ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "custom_speed:", AudioStates.waiting_for_action)
async def cb_custom_speed_request(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AudioStates.waiting_for_speed)
    await call.message.edit_text(
        f"🎚 Введите скорость от <b>{MIN_SPEED}</b> до <b>{MAX_SPEED}</b>\n"
        "Например: <code>1.75</code> или <code>0.6</code>",
        reply_markup=cancel_only(),
        parse_mode="HTML",
    )
    await call.answer()


@router.message(AudioStates.waiting_for_speed)
async def handle_custom_speed_input(message: Message, state: FSMContext, bot: Bot) -> None:
    raw = message.text.strip().replace(",", ".")

    try:
        speed = float(raw)
    except ValueError:
        await message.answer(
            "❌ Введите число, например <code>1.75</code>",
            reply_markup=cancel_only(),
            parse_mode="HTML",
        )
        return

    if not (MIN_SPEED <= speed <= MAX_SPEED):
        await message.answer(
            f"❌ Скорость должна быть от <b>{MIN_SPEED}</b> до <b>{MAX_SPEED}</b>",
            reply_markup=cancel_only(),
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    proc_msg = await message.answer(
        f"⏳ Применяю скорость <b>{speed}×</b>...",
        parse_mode="HTML",
    )

    input_path: Optional[Path]  = None
    output_path: Optional[Path] = None

    try:
        input_path  = await _download_to_temp(bot, data["file_id"], data["filename"])
        output_path = await change_speed(input_path, speed)

        await _send_result(
            message,
            output_path,
            caption=f"✅ 🎚 Custom {speed}×\n📁 {data['filename']}",
            input_path=input_path,
        )
        output_path = None

    except RuntimeError as e:
        logger.error("Custom speed processing error: %s", e)
        await message.answer(f"❌ Ошибка обработки: {e}")
    finally:
        cleanup(output_path)
        try:
            await proc_msg.delete()
        except Exception:
            pass

    await state.clear()
