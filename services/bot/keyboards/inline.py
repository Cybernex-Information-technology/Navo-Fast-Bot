"""
Telegram inline tugmalari generatori.
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


def make_media_keyboard(music_button_key: Optional[str] = None) -> InlineKeyboardMarkup:
    """Video ostidagi tugmalar: Qo'shiqni yuklab olish va ijtimoiy tarmoqlar."""
    rows: List[List[InlineKeyboardButton]] = []
    if music_button_key:
        rows.append([
            InlineKeyboardButton(
                text="🎵 Qo'shiqni yuklab olish (To'liq MP3)",
                callback_data=f"dl_aud:{music_button_key}"
            )
        ])
    rows.extend(get_promo_rows())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def make_promo_keyboard() -> InlineKeyboardMarkup:
    """Oddiy promo tugmalar to'plami."""
    return InlineKeyboardMarkup(inline_keyboard=get_promo_rows())
