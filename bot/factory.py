"""Bot 和 Dispatcher 的工厂函数。

create_bot() — 创建 aiogram Bot 实例，默认 HTML 解析模式。
create_dispatcher() — 创建 Dispatcher，注册启动/关闭回调、中间件和所有 Router。
"""

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from middleware import LoggingMiddleware
from services.database import close_db, init_db
from handlers import bookmark_router, help_router, start_router

logger = logging.getLogger(__name__)


async def _on_startup(dispatcher: Dispatcher) -> None:
    """Dispatcher 启动回调：初始化数据库连接池并建表。"""
    await init_db()
    logger.info("Database initialized")


async def _on_shutdown(dispatcher: Dispatcher) -> None:
    """Dispatcher 关闭回调：释放数据库连接池。"""
    await close_db()
    logger.info("Database connection closed")


def create_dispatcher() -> Dispatcher:
    """创建并配置 Dispatcher，注册所有 Router 和中间件。"""
    dp = Dispatcher()
    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.include_router(start_router)
    dp.include_router(help_router)
    dp.include_router(bookmark_router)
    return dp


def create_bot() -> Bot:
    """创建 Bot 实例，使用 HTML 解析模式和配置中的 token。"""
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
