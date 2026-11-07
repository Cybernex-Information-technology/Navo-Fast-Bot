"""
Musiqani audio va videodan aniqlash xizmati (Shazam + Metadata).
Faqat videodagi qisqa parcha emas, butun qo'shiqning to'liq variantini
topish uchun xizmat qiladi.
"""
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger("recognizer")


def prepare_sample_for_shazam(media_path: Path) -> Path:
    """Shazam uchun eng maqbul 25 soniyalik toza mono WAV audio tayyorlash."""
    out_wav = media_path.with_name("sample_shazam.wav")
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(media_path),
            "-vn", "-ac", "1", "-ar", "44100",
            "-t", "25", str(out_wav)
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        return out_wav
    except Exception as e:
        log.warning("ffmpeg orqali sample tayyorlashda xatolik: %s. Asl fayl ishlatiladi.", e)
        return media_path


async def recognize_track(media_path: Path, media_info: Optional[Dict[str, Any]] = None) -> Optional[Tuple[str, str]]:
    """
    Qo'shiq nomi va ijrochisini aniqlaydi.
    1. Birinchi navbatda video metama'lumotlarini tekshiradi (Instagram/TikTok/YouTube teglari).
    2. Agar metama'lumotda bo'lmasa, Shazam orqali aniqlaydi.
    """
    # 1. Metama'lumotlarni tekshirish (juda tez va serverni qiynamaydi)
    if media_info:
        track = media_info.get("track")
        artist = media_info.get("artist") or media_info.get("creator") or media_info.get("uploader")
        if track:
            log.info("Metama'lumotdan musiqa topildi: %s - %s", artist or "", track)
            return track, artist or ""

    # 2. Shazam orqali aniqlash
    try:
        from shazamio import Shazam
    except ImportError:
        log.warning("shazamio kutubxonasi o'rnatilmagan")
        return None

    try:
        sample_file = await asyncio.to_thread(prepare_sample_for_shazam, media_path)
        shazam = Shazam()
        fn = getattr(shazam, "recognize", None) or getattr(shazam, "recognize_song", None)
        if not fn:
            return None

        out = await fn(str(sample_file))
        track_data = out.get("track")
        if track_data and track_data.get("title"):
            title = track_data.get("title", "").strip()
            subtitle = track_data.get("subtitle", "").strip()
            log.info("Shazam muvaffaqiyatli aniqladi: %s — %s", subtitle, title)
            return title, subtitle
    except Exception as e:
        log.warning("Shazam tahlilida xatolik: %s", e)

    return None
