"""
Navo Fast Bot — Production Entrypoint (Microservice Architecture)
Developed by CyberNexTeam
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault

from core.config import BOT_TOKEN
from core.database import close_db, init_db
from services.bot.handlers import (
    admin_router,
    media_router,
    music_router,
    start_router,
)
from services.bot.middlewares import UserTrackerMiddleware
from services.downloader.cleaner import cleanup_old_temp_files

# Log sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("navo_main")


async def setup_bot_menu(bot: Bot):
    """
    Telegramning chap pastki burchagidagi ko'k [≡ Menyu] tugmasini sozlash.
    Foydalanuvchilar qidirib o'tirmasdan tugma orqali start, help va stat ni ko'radi.
    """
    commands = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="help", description="ℹ️ Yordam va qo'llanma"),
        BotCommand(command="stat", description="📊 Statistika va Admin panel"),
    ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        log.info("Telegram Menyu tugmasi muvaffaqiyatli o'rnatildi.")
    except Exception as e:
        log.warning("Telegram menyu buyruqlarini o'rnatishda ogohlantirish: %s", e)


async def main():
    log.info("Navo Fast Bot ishga tushirilmoqda...")

    if not BOT_TOKEN:
        log.critical("XATOLIK: .env faylida BOT_TOKEN topilmadi! .env.example asosida .env faylini to'ldiring.")
        sys.exit(1)

    # 1. Ma'lumotlar bazasini initsializatsiya qilish
    await init_db()
    log.info("Ma'lumotlar bazasi (PostgreSQL) muvaffaqiyatli ulandi.")

    # 2. Qolib ketgan eski vaqtinchalik fayllarni tozalash
    cleanup_old_temp_files(max_age_seconds=1800)

    # 3. Bot va Dispatcher sozlash
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # 4. Foydalanuvchilarni avtomatik hisobga olish middleware'ini ulash
    dp.message.middleware(UserTrackerMiddleware())
    dp.callback_query.middleware(UserTrackerMiddleware())

    # 5. Routerni tartib bo'yicha ro'yxatga olish
    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(music_router)
    dp.include_router(media_router)

    # 6. Telegramdagi [≡ Menyu] tugmasini avtomatik chiqarish
    await setup_bot_menu(bot)

    # Bot ma'lumotlarini olish
    me = await bot.get_me()
    log.info("Bot tayyor va faoliyatini boshladi: @%s (ID: %s)", me.username, me.id)

    try:
        # Polling boshlash
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        log.info("Bot to'xtatilmoqda, sessiyalar yopilyapti...")
        await bot.session.close()
        await close_db()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot to'xtatildi.")
