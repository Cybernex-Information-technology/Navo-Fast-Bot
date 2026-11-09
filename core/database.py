"""
Ma'lumotlar bazasi boshqaruvi (PostgreSQL / asyncpg connection pool).

Ulanish manzili .env dagi DATABASE_URL orqali beriladi, masalan:
    DATABASE_URL=postgresql://navo:parol@localhost:5432/navo_bot

Tashqi interfeys (Database klassi metodlari) SQLite versiyasi bilan bir xil,
shuning uchun handlerlar va middleware'larni o'zgartirish shart emas.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import asyncpg

from core.config import DATABASE_URL, DB_POOL_MAX, DB_POOL_MIN

log = logging.getLogger("navo_db")

_pool: Optional[asyncpg.Pool] = None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id     BIGINT PRIMARY KEY,
    username        TEXT,
    full_name       TEXT,
    download_count  INTEGER NOT NULL DEFAULT 0,
    is_blocked      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS media_cache (
    url_hash      TEXT PRIMARY KEY,
    original_url  TEXT,
    media_type    TEXT,
    file_id       TEXT NOT NULL,
    title         TEXT,
    extra_json    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS persistent_buttons (
    key         TEXT PRIMARY KEY,
    data_json   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS download_logs (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT,
    media_type  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_media_cache_type   ON media_cache(media_type);
CREATE INDEX IF NOT EXISTS idx_users_active       ON users(last_active_at);
CREATE INDEX IF NOT EXISTS idx_logs_created       ON download_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_buttons_created    ON persistent_buttons(created_at);
"""

# Saqlanadigan tugma yozuvlarining maksimal soni (eskilari tozalanadi)
MAX_BUTTONS = 5000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_url(url: str, media_type: str = "video") -> str:
    norm = url.strip()
    return hashlib.sha256(f"{media_type}:{norm}".encode("utf-8")).hexdigest()[:32]


def _get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Ma'lumotlar bazasi ulanmagan: avval init_db() chaqiring.")
    return _pool


async def init_db() -> None:
    """PostgreSQL ga ulanish (pool) va jadvallarni yaratish."""
    global _pool
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL topilmadi! .env fayliga qo'shing, masalan: "
            "DATABASE_URL=postgresql://user:parol@host:5432/navo_bot"
        )
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=DB_POOL_MIN,
            max_size=DB_POOL_MAX,
            command_timeout=30,
        )
    async with _pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)


async def close_db() -> None:
    """Bot to'xtaganda pool'ni yopish."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


class Database:
    @staticmethod
    async def track_user(user_id: int, username: Optional[str], full_name: Optional[str]):
        """Foydalanuvchini ro'yxatga olish yoki oxirgi faolligini yangilash."""
        now = _now()
        await _get_pool().execute(
            """
            INSERT INTO users (telegram_id, username, full_name, created_at, last_active_at)
            VALUES ($1, $2, $3, $4, $4)
            ON CONFLICT (telegram_id) DO UPDATE SET
                username       = EXCLUDED.username,
                full_name      = EXCLUDED.full_name,
                last_active_at = EXCLUDED.last_active_at;
            """,
            user_id, username or "", full_name or "", now,
        )

    @staticmethod
    async def increment_user_downloads(user_id: int, media_type: str):
        """Yuklashlar hisoblagichini oshirish va log yozish."""
        now = _now()
        async with _get_pool().acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE users
                    SET download_count = download_count + 1, last_active_at = $1
                    WHERE telegram_id = $2;
                    """,
                    now, user_id,
                )
                await conn.execute(
                    """
                    INSERT INTO download_logs (user_id, media_type, created_at)
                    VALUES ($1, $2, $3);
                    """,
                    user_id, media_type, now,
                )

    @staticmethod
    async def get_cached_media(url: str, media_type: str = "video") -> Optional[Tuple[str, Optional[Dict]]]:
        """Keshdan file_id va qo'shimcha ma'lumotlarni olish."""
        row = await _get_pool().fetchrow(
            "SELECT file_id, extra_json FROM media_cache WHERE url_hash = $1;",
            _hash_url(url, media_type),
        )
        if row:
            extra = json.loads(row["extra_json"]) if row["extra_json"] else {}
            return row["file_id"], extra
        return None

    @staticmethod
    async def set_cached_media(url: str, media_type: str, file_id: str, title: str = "", extra: Optional[Dict] = None):
        """Keshga saqlash."""
        await _get_pool().execute(
            """
            INSERT INTO media_cache (url_hash, original_url, media_type, file_id, title, extra_json, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (url_hash) DO UPDATE SET
                file_id    = EXCLUDED.file_id,
                title      = EXCLUDED.title,
                extra_json = EXCLUDED.extra_json;
            """,
            _hash_url(url, media_type), url, media_type, file_id, title,
            json.dumps(extra or {}, ensure_ascii=False), _now(),
        )

    @staticmethod
    async def save_button_data(key: str, data: Dict[str, Any]):
        """Tugma ma'lumotlarini doimiy saqlash (eskirmaydi)."""
        async with _get_pool().acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO persistent_buttons (key, data_json, created_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (key) DO UPDATE SET
                        data_json  = EXCLUDED.data_json,
                        created_at = EXCLUDED.created_at;
                    """,
                    key, json.dumps(data, ensure_ascii=False), _now(),
                )
                # MAX_BUTTONS tadan oshib ketgan eng eski tugma yozuvlarini tozalash
                await conn.execute(
                    """
                    DELETE FROM persistent_buttons
                    WHERE created_at < (
                        SELECT created_at FROM persistent_buttons
                        ORDER BY created_at DESC
                        OFFSET $1 LIMIT 1
                    );
                    """,
                    MAX_BUTTONS - 1,
                )

    @staticmethod
    async def get_button_data(key: str) -> Optional[Dict[str, Any]]:
        """Tugma ma'lumotlarini bazadan o'qish."""
        value = await _get_pool().fetchval(
            "SELECT data_json FROM persistent_buttons WHERE key = $1;", key
        )
        return json.loads(value) if value else None

    @staticmethod
    async def get_statistics() -> Dict[str, Any]:
        """Admin panel uchun to'liq statistika."""
        row = await _get_pool().fetchrow(
            """
            SELECT
                (SELECT COUNT(*) FROM users)                                                 AS total_users,
                (SELECT COUNT(*) FROM users WHERE last_active_at >= NOW() - INTERVAL '1 day') AS today_users,
                (SELECT COUNT(*) FROM download_logs)                                         AS total_downloads,
                (SELECT COUNT(*) FROM download_logs WHERE created_at >= NOW() - INTERVAL '1 day') AS today_downloads,
                (SELECT COUNT(*) FROM media_cache)                                           AS cache_count;
            """
        )
        return {k: int(row[k]) for k in (
            "total_users", "today_users", "total_downloads", "today_downloads", "cache_count"
        )}

    @staticmethod
    async def get_all_user_ids() -> List[int]:
        """Broadcast (xabar tarqatish) uchun barcha foydalanuvchilar ID ro'yxati."""
        rows = await _get_pool().fetch(
            "SELECT telegram_id FROM users WHERE is_blocked = FALSE;"
        )
        return [r["telegram_id"] for r in rows]
