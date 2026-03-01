"""
services/audio_processor.py — Ядро обработки аудио.

Все операции делаются через ffmpeg:
  • Изменение скорости (с сохранением тональности) — фильтр atempo
  • Изменение тональности (pitch shift)           — фильтр rubberband
    (fallback: asetrate + aresample, если rubberband недоступен)
  • Комбо: скорость + питч одновременно

Файлы именуются UUID, удаляются после обработки.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional

from bot.config import TEMP_DIR, PROCESSING_TIMEOUT_SEC

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────────────────────────────────────

def _unique_path(suffix: str = ".mp3") -> Path:
    """Генерирует уникальный временный путь."""
    return TEMP_DIR / f"{uuid.uuid4().hex}{suffix}"


def _build_atempo_chain(speed: float) -> str:
    """
    atempo поддерживает только диапазон [0.5, 2.0].
    Для значений вне диапазона цепочка составляется рекурсивно.

    Примеры:
        0.25 → atempo=0.5,atempo=0.5
        4.0  → atempo=2.0,atempo=2.0
        0.75 → atempo=0.75
    """
    filters: list[str] = []
    remaining = speed

    if remaining < 0.5:
        # Разбиваем: каждый шаг минимум 0.5
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
    elif remaining > 2.0:
        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0

    filters.append(f"atempo={remaining:.6f}")
    return ",".join(filters)


def _check_rubberband() -> bool:
    """Проверяет наличие ffmpeg-фильтра rubberband."""
    return shutil.which("ffmpeg") is not None  # упрощённая проверка


async def _run_ffmpeg(args: list[str], timeout: int = PROCESSING_TIMEOUT_SEC) -> None:
    """Запускает ffmpeg асинхронно, бросает RuntimeError при ошибке."""
    cmd = ["ffmpeg", "-y"] + args
    logger.debug("Running: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"ffmpeg превысил лимит {timeout}с")

    if proc.returncode != 0:
        err = stderr.decode(errors="replace")
        logger.error("ffmpeg error:\n%s", err)
        raise RuntimeError(f"ffmpeg завершился с кодом {proc.returncode}")


# ──────────────────────────────────────────────────────────────────────────────
# Публичный API
# ──────────────────────────────────────────────────────────────────────────────

async def change_speed(
    input_path: Path,
    speed: float,
    output_suffix: str = ".mp3",
) -> Path:
    """
    Меняет скорость аудио с сохранением тональности через atempo.

    Args:
        input_path:    путь к исходному файлу
        speed:         коэффициент скорости (0.25 – 4.0)
        output_suffix: расширение выходного файла

    Returns:
        Путь к обработанному файлу (нужно удалить после использования)
    """
    output_path = _unique_path(output_suffix)
    atempo = _build_atempo_chain(speed)

    await _run_ffmpeg([
        "-i", str(input_path),
        "-filter:a", atempo,
        "-vn",                    # убираем видеопоток, если есть
        "-ar", "44100",           # фиксируем sample rate
        "-ac", "2",               # стерео
        "-b:a", "192k",
        str(output_path),
    ])

    logger.info("Speed changed: %.2fx → %s", speed, output_path.name)
    return output_path


async def change_pitch(
    input_path: Path,
    semitones: int,
    output_suffix: str = ".mp3",
) -> Path:
    """
    Сдвигает тональность на указанное количество полутонов.

    Стратегия:
      1. Пробуем rubberband (лучшее качество)
      2. Fallback: asetrate + aresample (меняет питч, но и скорость — компенсируем atempo)

    Args:
        input_path: путь к исходному файлу
        semitones:  количество полутонов (-12 … +12)
    """
    output_path = _unique_path(output_suffix)

    # Коэффициент изменения частоты: 2^(n/12)
    pitch_ratio = 2 ** (semitones / 12)

    try:
        # ── Попытка 1: rubberband ──────────────────────────────────────────
        await _run_ffmpeg([
            "-i", str(input_path),
            "-filter:a",
            f"rubberband=pitch={pitch_ratio:.6f}",
            "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            str(output_path),
        ])
    except RuntimeError:
        # ── Fallback: asetrate → atempo → aresample ────────────────────────
        logger.warning("rubberband недоступен, используем asetrate fallback")
        output_path = _unique_path(output_suffix)  # новый путь

        # Меняем sample rate → питч меняется, скорость тоже
        # Компенсируем скорость обратным atempo
        new_rate = int(44100 * pitch_ratio)
        comp_speed = 1.0 / pitch_ratio
        atempo_comp = _build_atempo_chain(comp_speed)

        await _run_ffmpeg([
            "-i", str(input_path),
            "-filter:a",
            f"asetrate={new_rate},{atempo_comp},aresample=44100",
            "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            str(output_path),
        ])

    logger.info("Pitch shifted: %+d semitones → %s", semitones, output_path.name)
    return output_path


async def change_speed_and_pitch(
    input_path: Path,
    speed: float,
    semitones: int,
    output_suffix: str = ".mp3",
) -> Path:
    """
    Меняет скорость (с сохранением тональности) И тональность одновременно.
    Цепочка фильтров: atempo → rubberband (или fallback).
    """
    output_path = _unique_path(output_suffix)
    atempo = _build_atempo_chain(speed)
    pitch_ratio = 2 ** (semitones / 12)

    try:
        full_filter = f"{atempo},rubberband=pitch={pitch_ratio:.6f}"
        await _run_ffmpeg([
            "-i", str(input_path),
            "-filter:a", full_filter,
            "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            str(output_path),
        ])
    except RuntimeError:
        # Fallback без rubberband: сначала скорость, затем asetrate
        output_path = _unique_path(output_suffix)
        new_rate = int(44100 * pitch_ratio)
        comp_speed = 1.0 / pitch_ratio
        atempo_comp = _build_atempo_chain(comp_speed)

        full_filter = f"{atempo},asetrate={new_rate},{atempo_comp},aresample=44100"
        await _run_ffmpeg([
            "-i", str(input_path),
            "-filter:a", full_filter,
            "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            str(output_path),
        ])

    logger.info(
        "Speed+Pitch: %.2fx / %+d st → %s",
        speed, semitones, output_path.name,
    )
    return output_path


def cleanup(*paths: Optional[Path]) -> None:
    """Безопасно удаляет временные файлы."""
    for p in paths:
        if p and p.exists():
            try:
                p.unlink()
                logger.debug("Deleted temp file: %s", p)
            except OSError as e:
                logger.warning("Could not delete %s: %s", p, e)
