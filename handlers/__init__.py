"""Handler Router 统一导出 — 每个子模块暴露一个 Router 实例。"""

from .bookmark import router as bookmark_router
from .help import router as help_router
from .start import router as start_router

__all__ = ["bookmark_router", "help_router", "start_router"]
