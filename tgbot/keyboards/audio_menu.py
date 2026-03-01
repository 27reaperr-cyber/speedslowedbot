"""
keyboards/audio_menu.py — Все inline-клавиатуры бота.

Структура callback_data:
  action:value
  Примеры:
    speed:1.25
    speed:0.75
    pitch:+1
    pitch:-2
    custom_speed:     (запрашиваем ввод)
    cancel:
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    """Главное меню после получения аудио."""
    builder = InlineKeyboardBuilder()

    # ── Speed Up ──────────────────────────────────────────────────────────
    builder.row(
        InlineKeyboardButton(text="🚀 Speed Up", callback_data="section:speed_up"),
    )
    builder.row(
        InlineKeyboardButton(text="1.25×", callback_data="speed:1.25"),
        InlineKeyboardButton(text="1.5×",  callback_data="speed:1.5"),
        InlineKeyboardButton(text="2×",    callback_data="speed:2.0"),
    )

    # ── Slowed ────────────────────────────────────────────────────────────
    builder.row(
        InlineKeyboardButton(text="🐌 Slowed", callback_data="section:slowed"),
    )
    builder.row(
        InlineKeyboardButton(text="0.75×", callback_data="speed:0.75"),
        InlineKeyboardButton(text="0.5×",  callback_data="speed:0.5"),
    )

    # ── Pitch ─────────────────────────────────────────────────────────────
    builder.row(
        InlineKeyboardButton(text="🎵 Pitch Shift", callback_data="section:pitch"),
    )
    builder.row(
        InlineKeyboardButton(text="▲ +1 st",  callback_data="pitch:+1"),
        InlineKeyboardButton(text="▲ +2 st",  callback_data="pitch:+2"),
        InlineKeyboardButton(text="▼ -1 st",  callback_data="pitch:-1"),
        InlineKeyboardButton(text="▼ -2 st",  callback_data="pitch:-2"),
    )

    # ── Custom speed ──────────────────────────────────────────────────────
    builder.row(
        InlineKeyboardButton(text="🎚 Custom speed", callback_data="custom_speed:"),
    )

    # ── Cancel ────────────────────────────────────────────────────────────
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel:"),
    )

    return builder.as_markup()


def confirm_menu(action_label: str) -> InlineKeyboardMarkup:
    """Кнопка 'назад' после показа описания действия."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"✅ Применить: {action_label}", callback_data="confirm:"),
        InlineKeyboardButton(text="◀ Назад", callback_data="back:"),
    )
    return builder.as_markup()


def back_only() -> InlineKeyboardMarkup:
    """Только кнопка 'назад'."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀ Назад", callback_data="back:"))
    return builder.as_markup()


def cancel_only() -> InlineKeyboardMarkup:
    """Только кнопка 'отмена' (при ожидании ввода числа)."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel:"))
    return builder.as_markup()
