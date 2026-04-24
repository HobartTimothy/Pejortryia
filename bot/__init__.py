import logging
import asyncio

from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.factory import create_bot, create_dispatcher
from config import settings
from utils import setup_logging

logger = logging.getLogger(__name__)


async def _health(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def _hook(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "message": "配置成功"})


async def main() -> None:
    setup_logging(settings.log_level)
    bot = create_bot()
    dp = create_dispatcher()
    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret,
    ).register(app, path=settings.webhook_path)

    app.router.add_get("/health", _health)
    app.router.add_get("/hook", _hook)
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
