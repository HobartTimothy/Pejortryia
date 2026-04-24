import logging
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

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
    """Bot 主流程：初始化日志 → 创建 Bot/Dispatcher → 启动 Webhook 服务。"""
    setup_logging(settings.log_level)
    bot = create_bot()
    dp = create_dispatcher()
    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret,
    ).register(app, path=settings.webhook_path)
    app.router.add_get("/health", lambda _: web.Response(text="ok"))
    setup_application(app, dp, bot=bot)

    webhook_url = f"{settings.webhook_base_url}{settings.webhook_path}"
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret,
        drop_pending_updates=True,
    )
    logger.info("Webhook configured: %s", webhook_url)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.webhook_host, port=settings.webhook_port)
    await site.start()
    logger.info("Webhook server started on %s:%s", settings.webhook_host, settings.webhook_port)

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
