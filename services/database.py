"""数据库访问层。

使用 asyncpg 连接池管理 PostgreSQL 连接。
模块通过 init_db() 初始化连接池，close_db() 关闭，
各 CRUD 函数从池中获取连接执行查询。
"""

from __future__ import annotations

import asyncpg

from config import settings

# 模块级连接池，由 init_db() 初始化
_pool: asyncpg.Pool | None = None

# 应用启动时自动建表（CREATE TABLE IF NOT EXISTS，幂等操作）
_SCHEMA = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id          SERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    msg_type    TEXT NOT NULL,
    summary     TEXT,
    file_id     TEXT,
    chat_id     BIGINT,
    message_id  INTEGER,
    source_type TEXT,
    source_name TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_created ON bookmarks(user_id, created_at DESC);
"""


async def init_db() -> None:
    """初始化连接池并执行建表 DDL。启动时由 Dispatcher 回调调用。"""
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
    )
    async with _pool.acquire() as conn:
        await conn.execute(_SCHEMA)


async def close_db() -> None:
    """关闭连接池。关闭时由 Dispatcher 回调调用。"""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _db() -> asyncpg.Pool:
    """获取已初始化的连接池，未初始化时断言失败。"""
    assert _pool is not None, "Database not initialized — call init_db() first"
    return _pool


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
    """插入一条收藏记录，返回自增 id。"""
    return await _db().fetchval(
        """INSERT INTO bookmarks (user_id, msg_type, summary, file_id, chat_id, message_id, source_type, source_name)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
           RETURNING id""",
        user_id,
        msg_type,
        summary,
        file_id,
        chat_id,
        message_id,
        source_type,
        source_name,
    )


async def count_bookmarks(user_id: int) -> int:
    """返回指定用户的收藏总数。"""
    return await _db().fetchval("SELECT COUNT(*) FROM bookmarks WHERE user_id = $1", user_id)


async def list_bookmarks(user_id: int, page: int, page_size: int = 5) -> list[dict]:
    """分页查询用户的收藏列表，按创建时间倒序。"""
    offset = page * page_size
    rows = await _db().fetch(
        "SELECT * FROM bookmarks WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
        user_id,
        page_size,
        offset,
    )
    return [dict(row) for row in rows]


async def get_bookmark(user_id: int, bookmark_id: int) -> dict | None:
    """获取单条收藏详情，需用户 ID 匹配以保证数据隔离。"""
    row = await _db().fetchrow(
        "SELECT * FROM bookmarks WHERE id = $1 AND user_id = $2",
        bookmark_id,
        user_id,
    )
    return dict(row) if row else None


async def delete_bookmark(user_id: int, bookmark_id: int) -> bool:
    """删除收藏记录，需用户 ID 匹配。返回 True 表示成功删除。"""
    result = await _db().execute(
        "DELETE FROM bookmarks WHERE id = $1 AND user_id = $2",
        bookmark_id,
        user_id,
    )
    # asyncpg 的 execute() 返回状态字符串如 "DELETE 1" 或 "DELETE 0"
    deleted = int(result.split()[-1]) if result else 0
    return deleted > 0
