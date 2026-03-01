from __future__ import annotations

from aiogram import Router


def get_main_router() -> Router:
    """Ленивая инициализация роутеров — избегает circular imports."""
    from bot.handlers.common import router as common_router
    from bot.handlers.audio import router as audio_router

    main_router = Router(name="main")
    main_router.include_router(common_router)
    main_router.include_router(audio_router)
    return main_router


# Совместимость со старым импортом
main_router = get_main_router()

__all__ = ["main_router", "get_main_router"]
