"""
Telegram inline tugmalari generatori (@SongFastBot uslubida).
"""
from typing import List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from core.config import BOT_USERNAME, CHANNEL_URL, INSTAGRAM_URL


def get_promo_rows() -> List[List[InlineKeyboardButton]]:
    """Ijtimoiy tarmoqlar va guruhga qo'shish tugmalari."""
    rows: List[List[InlineKeyboardButton]] = []
    links: List[InlineKeyboardButton] = []

    if INSTAGRAM_URL:
        links.append(InlineKeyboardButton(text="📸 Instagram", url=INSTAGRAM_URL))
    if CHANNEL_URL:
        links.append(InlineKeyboardButton(text="📢 Telegram kanal", url=CHANNEL_URL))
    if links:
        rows.append(links)

    clean_bot_user = BOT_USERNAME.lstrip("@")
    rows.append([
        InlineKeyboardButton(
            text="➕ Guruhga qo'shish",
            url=f"https://t.me/{clean_bot_user}?startgroup=true"
        )
    ])
    return rows


def make_media_keyboard(button_key: Optional[str] = None, **kwargs) -> InlineKeyboardMarkup:
    """
    Video ostidagi asosiy tugmalar:
    1. To'liq MP3 qo'shiqni yuklab olish (YouTube dan to'liq original MP3)
    2. Dumaloq video (Teleskop / Round Video Note) qilib berish
    3. Ijtimoiy tarmoqlar va guruhga qo'shish
    """
    key = button_key or kwargs.get("music_button_key")
    rows: List[List[InlineKeyboardButton]] = []
    if key:
        rows.append([
            InlineKeyboardButton(
                text="🎵 Qo'shiqni yuklab olish (To'liq MP3)",
                callback_data=f"dl_aud:{key}"
            )
        ])
        rows.append([
            InlineKeyboardButton(
                text="🎥 Dumaloq video (Teleskop)",
                callback_data=f"dl_round:{key}"
            )
        ])
    rows.extend(get_promo_rows())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def make_promo_keyboard() -> InlineKeyboardMarkup:
    """Oddiy promo tugmalar to'plami."""
    return InlineKeyboardMarkup(inline_keyboard=get_promo_rows())
