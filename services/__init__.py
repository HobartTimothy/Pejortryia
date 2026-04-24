"""服务层统一导出 — 数据库操作函数。"""

from .database import add_bookmark, close_db, count_bookmarks, delete_bookmark, get_bookmark, init_db, list_bookmarks

__all__ = [
    "add_bookmark",
    "close_db",
    "count_bookmarks",
    "delete_bookmark",
    "get_bookmark",
    "init_db",
    "list_bookmarks",
]
