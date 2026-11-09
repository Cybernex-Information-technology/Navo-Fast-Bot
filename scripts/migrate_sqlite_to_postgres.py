"""
Eski SQLite bazasidagi (data/bot.db) ma'lumotlarni PostgreSQL ga ko'chirish.
Bir marta ishga tushiriladi. Qayta ishga tushirilsa, takroriy yozuvlar o'tkazib yuboriladi.

Ishlatish (loyiha ildiz papkasidan, .env da DATABASE_URL bo'lishi kerak):
    python scripts/migrate_sqlite_to_postgres.py data/bot.db
"""
import asyncio
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import _get_pool, close_db, init_db  # noqa: E402


def _ts(value):
    """SQLite dagi ISO matn vaqtini timezone'li datetime ga aylantirish."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace(" ", "T"))
    except ValueError:
        return datetime.now(timezone.utc)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def main(sqlite_path: str):
    if not Path(sqlite_path).is_file():
        sys.exit(f"SQLite fayl topilmadi: {sqlite_path}")

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row
    await init_db()
    pool = _get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            users = src.execute("SELECT * FROM users").fetchall()
            await conn.executemany(
                """
                INSERT INTO users (telegram_id, username, full_name, download_count,
                                   is_blocked, created_at, last_active_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (telegram_id) DO NOTHING;
                """,
                [(r["telegram_id"], r["username"], r["full_name"], r["download_count"] or 0,
                  bool(r["is_blocked"]), _ts(r["created_at"]), _ts(r["last_active_at"]))
                 for r in users],
            )

            cache = src.execute("SELECT * FROM media_cache").fetchall()
            await conn.executemany(
                """
                INSERT INTO media_cache (url_hash, original_url, media_type, file_id,
                                         title, extra_json, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (url_hash) DO NOTHING;
                """,
                [(r["url_hash"], r["original_url"], r["media_type"], r["file_id"],
                  r["title"], r["extra_json"], _ts(r["created_at"])) for r in cache],
            )

            buttons = src.execute("SELECT * FROM persistent_buttons").fetchall()
            await conn.executemany(
                """
                INSERT INTO persistent_buttons (key, data_json, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (key) DO NOTHING;
                """,
                [(r["key"], r["data_json"], _ts(r["created_at"])) for r in buttons],
            )

            # Loglar uchun id yangidan beriladi; skript qayta ishlatilsa
            # loglar ikki marta yozilmasligi uchun jadval bo'sh bo'lsagina ko'chiriladi.
            logs = []
            if await conn.fetchval("SELECT COUNT(*) FROM download_logs") == 0:
                logs = src.execute("SELECT * FROM download_logs").fetchall()
                await conn.executemany(
                    "INSERT INTO download_logs (user_id, media_type, created_at) VALUES ($1, $2, $3);",
                    [(r["user_id"], r["media_type"], _ts(r["created_at"])) for r in logs],
                )

    src.close()
    await close_db()
    print(f"Tayyor! users={len(users)}, media_cache={len(cache)}, "
          f"persistent_buttons={len(buttons)}, download_logs={len(logs)}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "data/bot.db"))
