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
        f"Men <b>Navo Fast Bot</b> — video va musiqalarni 1080p Full HD sifatda tez yuklovchi professional botman 🎬🎵\n\n"
        "📥 <b>Imkoniyatlar:</b>\n"
        "• <b>Instagram, TikTok, YouTube</b> — videoni eng yuqori sifatda (1080p) yuklab beraman\n"
        "• 🎵 <b>«Qo'shiqni yuklab olish»</b> — videodan to'liq original MP3 qo'shiqni topib beradi (Shazam AI)\n"
        "• 🎥 <b>«Dumaloq video (Teleskop)»</b> — istalgan videoni Telegram krujochek (video note) qilib beradi\n"
        "• 🔎 Qo'shiq yoki ijrochi nomini yozing — 5 ta variant ichidan tanlang\n"
        "• 🎙 Ovozli xabar (voice) yoki audio yuboring — musiqani aniqlab, to'liq MP3 sini topib beraman\n\n"
        f"⚡ <i>Tez, barqaror va qulay — {TEAM_NAME}</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=make_promo_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "ℹ️ <b>Botdan qanday foydalaniladi?</b>\n\n"
        "1️⃣ <b>Video yuklash:</b> Instagram Reel, TikTok yoki YouTube havolasini botga yuboring.\n"
        "2️⃣ <b>To'liq qo'shiqni olish:</b> Video ostidagi <i>«Qo'shiqni yuklab olish (To'liq MP3)»</i> tugmasini bosing.\n"
        "3️⃣ <b>Dumaloq video qilish:</b> Video ostidagi <i>«Dumaloq video (Teleskop)»</i> tugmasini bosing.\n"
        "4️⃣ <b>Nom bo'yicha qidirish:</b> Qo'shiq yoki ijrochi nomini yozing (masalan: <code>Jaloliddin Ahmadaliyev</code>).\n"
        "5️⃣ <b>Musiqani aniqlash:</b> Video yoki audio parcha tashlang — bot musiqani o'zi aniqlab beradi.\n\n"
        "⚡ <i>Barcha yuklashlar eng yuqori Full HD sifatda amalga oshiriladi.</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=make_promo_keyboard())
