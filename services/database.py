from __future__ import annotations

import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "bookmarks.db"

_connection: aiosqlite.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    msg_type    TEXT NOT NULL,
    summary     TEXT,
    file_id     TEXT,
    chat_id     INTEGER,
    message_id  INTEGER,
    source_type TEXT,
    source_name TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_created ON bookmarks(user_id, created_at DESC);
"""


async def init_db() -> None:
    global _connection
    _connection = await aiosqlite.connect(DB_PATH)
    _connection.row_factory = aiosqlite.Row
    await _connection.executescript(_SCHEMA)
    await _connection.commit()


async def close_db() -> None:
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None


def _db() -> aiosqlite.Connection:
    assert _connection is not None, "Database not initialized — call init_db() first"
    return _connection


async def add_bookmark(
    user_id: int,
    msg_type: str,
    summary: str | None = None,
    file_id: str | None = None,
    chat_id: int | None = None,
    message_id: int | None = None,
    source_type: str | None = None,
    source_name: str | None = None,
) -> int:
    db = _db()
    cursor = await db.execute(
        """INSERT INTO bookmarks (user_id, msg_type, summary, file_id, chat_id, message_id, source_type, source_name)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, msg_type, summary, file_id, chat_id, message_id, source_type, source_name),
    )
    await db.commit()
    return cursor.lastrowid  # type: ignore[return-value]


async def count_bookmarks(user_id: int) -> int:
    db = _db()
    cursor = await db.execute("SELECT COUNT(*) FROM bookmarks WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    return row[0]


async def list_bookmarks(user_id: int, page: int, page_size: int = 5) -> list[dict]:
    db = _db()
    offset = page * page_size
    cursor = await db.execute(
        "SELECT * FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, page_size, offset),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_bookmark(user_id: int, bookmark_id: int) -> dict | None:
    db = _db()
    cursor = await db.execute(
        "SELECT * FROM bookmarks WHERE id = ? AND user_id = ?",
        (bookmark_id, user_id),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def delete_bookmark(user_id: int, bookmark_id: int) -> bool:
    db = _db()
    cursor = await db.execute(
        "DELETE FROM bookmarks WHERE id = ? AND user_id = ?",
        (bookmark_id, user_id),
    )
    await db.commit()
    return cursor.rowcount > 0
