import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from middleware import LoggingMiddleware
from services.database import close_db, init_db
from handlers import bookmark_router, help_router, start_router

logger = logging.getLogger(__name__)


async def _on_startup(dispatcher: Dispatcher) -> None:
    await init_db()
    logger.info("Database initialized")


async def _on_shutdown(dispatcher: Dispatcher) -> None:
    await close_db()
    logger.info("Database connection closed")


def create_dispatcher() -> Dispatcher:
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
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
