"""
Qo'shiqlarni qidirish va natijalarni formatlash xizmati.
"""
import html
from typing import Any, Dict, List, Tuple

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.downloader.ytdlp_engine import search_youtube_videos


def format_duration(sec: int) -> str:
    """Soniyalarni mm:ss formatiga o'tkazish."""
    if not sec:
        return "--:--"
    return f"{sec // 60}:{sec % 60:02d}"


def build_search_response(query: str, results: List[Dict[str, Any]]) -> Tuple[str, InlineKeyboardMarkup]:
    """
    Qidiruv natijalari matni va tugmalarini tayyorlash.
    Tugmalar eskirib qolmaydi, chunki YouTube ID to'g'ridan-to'g'ri callback_data ichida bo'ladi!
    """
    safe_q = html.escape(query)
    lines = [f"🎵 <b>{safe_q}</b>\n"]

    buttons = []
    for i, r in enumerate(results, 1):
        title = html.escape(r["title"])
        dur = format_duration(r["duration"])
        lines.append(f"<b>{i}.</b> {title} <b>[{dur}]</b>")
        # YouTube ID odatda 11 belgidan iborat (masalan: dl_yt:xzvuuVkrKnc - 17 bayt, Telegram limiti 64 bayt)
        buttons.append(
            InlineKeyboardButton(text=str(i), callback_data=f"dl_yt:{r['id']}")
        )

    lines.append("\n👇 <i>Kerakli raqamni tanlang, to'liq MP3 formatda yuboriladi:</i>")

    # 5 ta tugmani bir qatorda chiroyli chiqarish
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    return "\n".join(lines), keyboard
