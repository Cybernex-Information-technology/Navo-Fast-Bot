"""
Musiqani audio va videodan aniqlash xizmati (Shazam + Metadata).
Videodan to'liq original qo'shiqni aniqlaydi (@SongFastBot uslubida).
"""
import asyncio
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger("recognizer")

GENERIC_AUDIO_NAMES = {
    "original audio", "original sound", "asl audio", "asl ovoz",
    "original", "sound", "audio", "video by", "audio by", "sound by",
    "unknown", "nomsiz", "voice", "audio track", "track", "music",
    "original ton", "son original", "suono originale", "sonido original",
    "ursprünglicher ton", "som original", "оригинальный звук", "оригинальное аудио"
}


def is_generic_audio(name: Optional[str]) -> bool:
    """Audio nomi umumiy (original sound kabi) ekanligini tekshirish."""
    if not name:
        return True
    cleaned = str(name).strip().lower()
    if len(cleaned) < 2:
        return True
    for g in GENERIC_AUDIO_NAMES:
        if g in cleaned:
            return True
    return False


def clean_title_for_search(text: str) -> Optional[str]:
    """Video izohidan (caption) xeshteg va keraksiz belgilarni tozalab, qidiruv matnini olish."""
    if not text:
        return None
    cleaned = re.sub(r"[#@]\S+", "", text)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"[^\w\s\-,–—'\"()]+", " ", cleaned).strip()
    if len(cleaned) < 3 or is_generic_audio(cleaned):
        return None
    return cleaned[:80].strip()


def slice_audio(input_path: Path, start_sec: int, duration_sec: int, output_path: Path) -> bool:
    """Audioni ma'lum oraliqda kesib olish."""
    try:
        cmd = [
            "ffmpeg", "-y", "-ss", str(start_sec), "-i", str(input_path),
            "-t", str(duration_sec),
            "-vn", "-ac", "1", "-ar", "44100",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return output_path.is_file() and output_path.stat().st_size > 1000
    except Exception as e:
        log.debug("Audio kesishda ogohlantirish: %s", e)
        return False


async def recognize_track(
    media_path: Path, media_info: Optional[Dict[str, Any]] = None
) -> Optional[Tuple[str, str]]:
    """
    Qo'shiq nomi va ijrochisini aniqlaydi.
    1. Metama'lumotlar (Instagram/TikTok dagi rasmiy qo'shiq nomi).
    2. Shazam sun'iy intellekti (avval boshidan, so'ngra 5-soniyadan keyin tahlil).
    3. Video sarlavhasi (description/title).
    """
    # 1. Metama'lumotlarni tekshirish (TikTok va Instagramdagi rasmiy musiqalar)
    if media_info:
        track = media_info.get("track") or media_info.get("music_title") or media_info.get("sound_title")
        artist = media_info.get("artist") or media_info.get("music_artist") or media_info.get("creator") or ""
        if track and not is_generic_audio(str(track)):
            log.info("Metama'lumotdan aniq musiqa topildi: %s - %s", artist, track)
            return str(track).strip(), str(artist).strip()

    # 2. Shazam AI orqali aniqlash
    try:
        from shazamio import Shazam
        shazam = Shazam()

        # 1-urinish: Audio faylning o'zini to'g'ridan-to'g'ri Shazamga berish
        out = await shazam.recognize(str(media_path))
        track_data = out.get("track") if out else None
        if track_data and track_data.get("title"):
            title = track_data.get("title", "").strip()
            subtitle = track_data.get("subtitle", "").strip()
            log.info("Shazam (1-urinish) aniqladi: %s — %s", subtitle, title)
            return title, subtitle

        # 2-urinish: Video boshida gap yoki pauza bo'lishi mumkinligi uchun 5-soniyadan keyingi 20 soniyalik qismni tahlil qilish
        sample_path = media_path.with_name("shazam_slice.wav")
        if slice_audio(media_path, start_sec=5, duration_sec=20, output_path=sample_path):
            out2 = await shazam.recognize(str(sample_path))
            track_data2 = out2.get("track") if out2 else None
            if track_data2 and track_data2.get("title"):
                title = track_data2.get("title", "").strip()
                subtitle = track_data2.get("subtitle", "").strip()
                log.info("Shazam (2-urinish, 5s dan) aniqladi: %s — %s", subtitle, title)
                return title, subtitle

    except Exception as e:
        log.warning("Shazam tahlilida xatolik: %s", e)

    # 3. Zaxira: Video sarlavhasidan qidiruv uchun matn ajratish
    if media_info:
        desc = media_info.get("description") or media_info.get("title")
        candidate = clean_title_for_search(desc or "")
        if candidate:
            log.info("Sarlavhadan musiqa qidiruv matni olindi: %s", candidate)
            return candidate, ""

    return None
