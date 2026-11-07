from services.bot.handlers.admin import router as admin_router
from services.bot.handlers.media import router as media_router
from services.bot.handlers.music import router as music_router
from services.bot.handlers.start import router as start_router

__all__ = ["start_router", "media_router", "music_router", "admin_router"]
