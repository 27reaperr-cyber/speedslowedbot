# 🎧 Speed Up & Slowed Bot

Telegram-бот для изменения скорости и тональности аудиофайлов.

## Возможности

| Кнопка | Описание |
|--------|----------|
| 🚀 Speed Up 1.25× / 1.5× / 2× | Ускорение с сохранением тональности |
| 🐌 Slowed 0.75× / 0.5× | Замедление с сохранением тональности |
| 🎵 Pitch ±1 / ±2 st | Сдвиг тональности на полутоны |
| 🎚 Custom speed | Любая скорость от 0.25 до 4.0 |

## Быстрый старт

### Локально

```bash
# 1. Клонировать репозиторий
git clone <repo>
cd speedup_bot

# 2. Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Установить ffmpeg
# Ubuntu/Debian: sudo apt install ffmpeg
# macOS:         brew install ffmpeg
# Windows:       winget install ffmpeg

# 5. (Опционально) rubberband для высококачественного pitch shift
# Ubuntu/Debian: sudo apt install rubberband-cli

# 6. Создать .env
cp .env.example .env
# Вставьте BOT_TOKEN в .env

# 7. Запуск
python main.py
```

### Docker

```bash
cp .env.example .env
# Заполните BOT_TOKEN в .env

docker-compose up -d
docker-compose logs -f
```

## Структура проекта

```
speedup_bot/
├── main.py                  # Точка входа
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── bot/
    ├── config.py            # Конфигурация из env
    ├── handlers/
    │   ├── __init__.py      # Объединение роутеров
    │   ├── common.py        # /start, /help
    │   └── audio.py         # Обработка аудио + FSM
    ├── services/
    │   ├── __init__.py
    │   └── audio_processor.py  # ffmpeg-интеграция
    └── keyboards/
        ├── __init__.py
        └── audio_menu.py    # Inline-клавиатуры
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
|-----------|-------------|----------|
| `BOT_TOKEN` | — | Токен бота (обязателен) |
| `TEMP_DIR` | `/tmp/audio_bot` | Временные файлы |
| `MAX_FILE_SIZE_MB` | `50` | Лимит размера файла |
| `PROCESSING_TIMEOUT_SEC` | `120` | Таймаут ffmpeg |

## Архитектура обработки аудио

```
Пользователь → аудиофайл
    ↓
Telegram Bot API (download)
    ↓
UUID temp file (/tmp/audio_bot/xxxxxxxx.mp3)
    ↓
ffmpeg filter chain:
  • Speed:  atempo=<value>  (цепочка для значений вне [0.5, 2.0])
  • Pitch:  rubberband=pitch=<ratio>
            (fallback: asetrate + atempo компенсация)
    ↓
UUID output file
    ↓
Telegram Bot API (send_audio)
    ↓
Удаление обоих temp файлов
```
