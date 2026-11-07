"""
Ma'lumotlar bazasi boshqaruvi (SQLite / WAL mode).
Hech qanday qo'shimcha tashqi kutubxonalarga bog'liq emas, 
millionlab yozuvlarni tez va ishonchli saqlaydi, server o'chganda ma'lumotlar yo'qolmaydi.
"""
import asyncio
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.config import DATABASE_PATH


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db():
    """Jadvallarni yaratish va indekslarni sozlash."""
    conn = _get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                download_count INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active_at TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS media_cache (
                url_hash TEXT PRIMARY KEY,
                original_url TEXT,
                media_type TEXT,
                file_id TEXT,
                title TEXT,
                extra_json TEXT,
                created_at TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS persistent_buttons (
                key TEXT PRIMARY KEY,
                data_json TEXT,
                created_at TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS download_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                media_type TEXT,
                created_at TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_media_cache_type ON media_cache(media_type);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_created ON download_logs(created_at);")
    conn.close()


def _hash_url(url: str, media_type: str = "video") -> str:
    norm = url.strip()
    return hashlib.sha256(f"{media_type}:{norm}".encode("utf-8")).hexdigest()[:32]


class Database:
    @staticmethod
    async def track_user(user_id: int, username: Optional[str], full_name: Optional[str]):
        """Foydalanuvchini ro'yxatga olish yoki oxirgi faolligini yangilash."""
        def _sync():
            now = datetime.now(timezone.utc).isoformat()
            conn = _get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO users (telegram_id, username, full_name, created_at, last_active_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(telegram_id) DO UPDATE SET
                        username = excluded.username,
                        full_name = excluded.full_name,
                        last_active_at = excluded.last_active_at;
                """, (user_id, username or "", full_name or "", now, now))
            conn.close()
        await asyncio.to_thread(_sync)

    @staticmethod
    async def increment_user_downloads(user_id: int, media_type: str):
        """Yuklashlar hisoblagichini oshirish va log yozish."""
        def _sync():
            now = datetime.now(timezone.utc).isoformat()
            conn = _get_connection()
            with conn:
                conn.execute("""
                    UPDATE users 
                    SET download_count = download_count + 1, last_active_at = ?
                    WHERE telegram_id = ?;
                """, (now, user_id))
                conn.execute("""
                    INSERT INTO download_logs (user_id, media_type, created_at)
                    VALUES (?, ?, ?);
                """, (user_id, media_type, now))
            conn.close()
        await asyncio.to_thread(_sync)

    @staticmethod
    async def get_cached_media(url: str, media_type: str = "video") -> Optional[Tuple[str, Optional[Dict]]]:
        """Keshdan file_id va qo'shimcha ma'lumotlarni olish."""
        def _sync():
            url_hash = _hash_url(url, media_type)
            conn = _get_connection()
            row = conn.execute("""
                SELECT file_id, extra_json FROM media_cache WHERE url_hash = ?;
            """, (url_hash,)).fetchone()
            conn.close()
            if row:
                extra = json.loads(row["extra_json"]) if row["extra_json"] else {}
                return row["file_id"], extra
            return None
        return await asyncio.to_thread(_sync)

    @staticmethod
    async def set_cached_media(url: str, media_type: str, file_id: str, title: str = "", extra: Optional[Dict] = None):
        """Keshga saqlash."""
        def _sync():
            url_hash = _hash_url(url, media_type)
            now = datetime.now(timezone.utc).isoformat()
            extra_str = json.dumps(extra or {}, ensure_ascii=False)
            conn = _get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO media_cache (url_hash, original_url, media_type, file_id, title, extra_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url_hash) DO UPDATE SET
                        file_id = excluded.file_id,
                        title = excluded.title,
                        extra_json = excluded.extra_json;
                """, (url_hash, url, media_type, file_id, title, extra_str, now))
            conn.close()
        await asyncio.to_thread(_sync)

    @staticmethod
    async def save_button_data(key: str, data: Dict[str, Any]):
        """Tugma ma'lumotlarini doimiy saqlash (eskirmaydi)."""
        def _sync():
            now = datetime.now(timezone.utc).isoformat()
            data_str = json.dumps(data, ensure_ascii=False)
            conn = _get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO persistent_buttons (key, data_json, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        data_json = excluded.data_json,
                        created_at = excluded.created_at;
                """, (key, data_str, now))
                # 5000 tadan oshib ketgan juda eski tugma yozuvlarini tozalash
                conn.execute("""
                    DELETE FROM persistent_buttons 
                    WHERE key NOT IN (
                        SELECT key FROM persistent_buttons ORDER BY created_at DESC LIMIT 5000
                    );
                """)
            conn.close()
        await asyncio.to_thread(_sync)

    @staticmethod
    async def get_button_data(key: str) -> Optional[Dict[str, Any]]:
        """Tugma ma'lumotlarini bazadan o'qish."""
        def _sync():
            conn = _get_connection()
            row = conn.execute("SELECT data_json FROM persistent_buttons WHERE key = ?;", (key,)).fetchone()
            conn.close()
            if row and row["data_json"]:
                return json.loads(row["data_json"])
            return None
        return await asyncio.to_thread(_sync)

    @staticmethod
    async def get_statistics() -> Dict[str, Any]:
        """Admin panel uchun to'liq statistika."""
        def _sync():
            conn = _get_connection()
            total_users = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
            
            # Bugungi faol foydalanuvchilar (oxirgi 24 soat)
            today_users = conn.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_active_at >= datetime('now', '-1 day');
            """).fetchone()[0]

            # Jami yuklashlar soni
            total_downloads = conn.execute("SELECT COUNT(*) FROM download_logs;").fetchone()[0]

            # Bugungi yuklashlar soni
            today_downloads = conn.execute("""
                SELECT COUNT(*) FROM download_logs 
                WHERE created_at >= datetime('now', '-1 day');
            """).fetchone()[0]

            # Keshdagi fayllar soni
            cache_count = conn.execute("SELECT COUNT(*) FROM media_cache;").fetchone()[0]

            conn.close()
            return {
                "total_users": total_users,
                "today_users": today_users,
                "total_downloads": total_downloads,
                "today_downloads": today_downloads,
                "cache_count": cache_count,
            }
        return await asyncio.to_thread(_sync)

    @staticmethod
    async def get_all_user_ids() -> List[int]:
        """Broadcast (xabar tarqatish) uchun barcha foydalanuvchilar ID ro'yxati."""
        def _sync():
            conn = _get_connection()
            rows = conn.execute("SELECT telegram_id FROM users WHERE is_blocked = 0;").fetchall()
            conn.close()
            return [r[0] for r in rows]
        return await asyncio.to_thread(_sync)
