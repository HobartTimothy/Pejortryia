import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from middleware import LoggingMiddleware
from routers import bookmark_router, help_router, start_router
from services.database import close_db, init_db
from utils.logging import setup_logging

logger = logging.getLogger(__name__)


async def _on_startup(dispatcher: Dispatcher) -> None:
    await init_db()
    logger.info("Database initialized")


async def _on_shutdown(dispatcher: Dispatcher) -> None:
    await close_db()
    logger.info("Database connection closed")


def create_dispatcher() -> Dispatcher:
    """创建 Dispatcher 并注册中间件与路由。

    - 为 message 和 callback_query 事件添加日志中间件
    - 按顺序 include 各业务路由，新增路由需在此处注册
    """
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
    """创建 Bot 实例，默认使用 HTML 解析模式。"""
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def main() -> None:
    """Bot 主流程：初始化日志 → 创建 Bot/Dispatcher → 开始长轮询。"""
    setup_logging(settings.log_level)
    bot = create_bot()
    dp = create_dispatcher()
    logger.info("Starting Pejortryia bot...")
    await dp.start_polling(bot)
