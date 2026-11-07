"""
Admin panel va statistika buyruqlari (/admin, /stat, /broadcast).
Bot egasiga botni to'liq nazorat qilish imkoniyatini beradi.
"""
import asyncio
import logging
from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from core.config import ADMIN_IDS
from core.database import Database

log = logging.getLogger("admin")
router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish."""
    return user_id in ADMIN_IDS


@router.message(Command("admin", "stat", "stats"))
async def cmd_admin_stats(message: Message):
    user_id = message.from_user.id
    
    # Agar foydalanuvchi admin bo'lmasa, unga o'z ID raqamini ko'rsatish
    if not is_admin(user_id):
        await message.answer(
            f"🔒 <b>Siz admin emassiz!</b>\n\n"
            f"Sizning Telegram ID raqamingiz: <code>{user_id}</code>\n\n"
            f"💡 <i>Admin huquqini olish uchun ushbu ID raqamni loyihadagi <b>.env</b> fayliga quyidagicha yozing:</i>\n"
            f"<code>ADMIN_IDS={user_id}</code>\n\n"
            f"So'ng botni qayta ishga tushiring.",
            parse_mode="HTML"
        )
        return

    stats = await Database.get_statistics()
    text = (
        "📊 <b>Navo Fast Bot — Nazorat Paneli</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {stats['total_users']} ta\n"
        f"🟢 <b>Bugun faol bo'lganlar (24s):</b> {stats['today_users']} ta\n"
        f"📥 <b>Jami amalga oshirilgan yuklashlar:</b> {stats['total_downloads']} ta\n"
        f"⚡ <b>Bugungi yuklashlar:</b> {stats['today_downloads']} ta\n"
        f"💾 <b>Keshdagi tayyor mediafayllar:</b> {stats['cache_count']} ta\n\n"
        "📢 <b>Xabar tarqatish:</b>\n"
        "Barcha foydalanuvchilarga xabar yuborish uchun quyidagicha yozing:\n"
        "<code>/broadcast Sizning xabaringiz matni...</code>\n"
        "<i>(Yoki biror xabarga reply qilib /broadcast yuboring)</i>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("🔒 Bu buyruq faqat bot adminlari uchun.")
        return

    # Tarqatiladigan xabarni aniqlash
    broadcast_msg = message.reply_to_message or message
    text_to_send = message.text.replace("/broadcast", "", 1).strip() if not message.reply_to_message else None

    if not message.reply_to_message and not text_to_send:
        await message.answer(
            "⚠️ Tarqatish uchun matn yozing yoki biror xabarga reply qilib /broadcast buyrug'ini yuboring.\n"
            "Masalan: <code>/broadcast Yangi imkoniyatlar qo'shildi!</code>",
            parse_mode="HTML",
        )
        return

    user_ids = await Database.get_all_user_ids()
    total = len(user_ids)
    if total == 0:
        await message.answer("Bazada foydalanuvchilar mavjud emas.")
        return

    status = await message.answer(f"📢 Xabar yuborish boshlandi. Jami qabul qiluvchilar: {total} ta...")

    sent_count = 0
    failed_count = 0

    for idx, uid in enumerate(user_ids, 1):
        try:
            if message.reply_to_message:
                await broadcast_msg.copy_to(chat_id=uid)
            else:
                await bot.send_message(chat_id=uid, text=text_to_send, parse_mode="HTML")
            sent_count += 1
        except Exception:
            failed_count += 1

        # Telegram FloodLimit cheklovini buzmaslik uchun har 25 ta xabardan so'ng biroz kutish
        if idx % 25 == 0:
            await asyncio.sleep(1.0)

    await status.edit_text(
        f"✅ <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"📤 Yuborildi: <b>{sent_count}</b> ta\n"
        f"❌ Yetib bormadi (bloklaganlar): <b>{failed_count}</b> ta",
        parse_mode="HTML"
    )
