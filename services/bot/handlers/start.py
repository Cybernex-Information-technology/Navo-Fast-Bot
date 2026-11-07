"""
/start va /help buyruqlari.
"""
import html
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from core.config import BOT_USERNAME, TEAM_NAME
from services.bot.keyboards.inline import make_promo_keyboard

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message):
    name = html.escape(message.from_user.first_name or "do'stim")
    clean_bot = BOT_USERNAME.lstrip("@")
    text = (
        f"👋 Assalomu alaykum, <b>{name}</b>!\n\n"
        f"Men <b>Navo Fast Bot</b> — video va musiqalarni yuqori sifatda tez yuklovchi botman 🎬🎵\n\n"
        "📥 <b>Imkoniyatlar:</b>\n"
        "• <b>Instagram, TikTok, YouTube</b> havolasini yuboring — videoni asl sifatda yuklab beraman\n"
        "• Video ostidagi <b>«Qo'shiqni yuklab olish»</b> tugmasi orqali to'liq MP3 qo'shiqni olasiz\n"
        "• Qo'shiq yoki ijrochi nomini yozing — 5 ta variant ichidan tanlang\n"
        "• Video, audio yoki ovozli xabar (voice) tashlang — qo'shiqni aniqlab, MP3 sini topib beraman\n\n"
        f"🚀 <i>Developed with quality by {TEAM_NAME}</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=make_promo_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "ℹ️ <b>Botdan qanday foydalaniladi?</b>\n\n"
        "1️⃣ <b>Video yuklash:</b> Instagram Reel, TikTok yoki YouTube havolasini shunchaki botga yuboring.\n"
        "2️⃣ <b>To'liq qo'shiqni olish:</b> Video yuklangach, uning ostidagi <i>«Qo'shiqni yuklab olish»</i> tugmasini bosing.\n"
        "3️⃣ <b>Nom bo'yicha qidirish:</b> Masalan: <code>Shahzoda Qora ko'zlaring</code> deb yozing va raqamlardan birini tanlang.\n"
        "4️⃣ <b>Qo'shiqni aniqlash:</b> Biror video yoki ovozli xabar tashlasangiz, bot musiqani o'zi aniqlaydi.\n\n"
        "⚡ <i>Barcha yuklashlar eng yuqori sifatda amalga oshiriladi.</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=make_promo_keyboard())
