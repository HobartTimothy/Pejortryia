"""Webhook 服务器模块。

基于 aiohttp 创建 HTTP 服务器，注册 webhook 路由、健康检查和配置验证端点，
启动时向 Telegram 注册 webhook URL。
"""

import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import settings

logger = logging.getLogger(__name__)


async def _health(request: web.Request) -> web.Response:
    """存活探针 — 供负载均衡或监控系统使用。"""
    return web.Response(text="ok")


async def _hook(request: web.Request) -> web.Response:
    """配置验证端点 — 确认 webhook 路径和 TLS 配置正确。"""
    return web.json_response({"status": "ok", "message": "配置成功"})


async def run_webhook_server(bot: Bot, dp: Dispatcher) -> None:
    """创建 aiohttp 应用，注册路由，设置 webhook，启动服务器并永久等待。

    Webhook URL 由 WEBHOOK_BASE_URL + WEBHOOK_PATH 拼接，
    启动时调用 set_webhook 向 Telegram 注册，drop_pending_updates=True
    避免积压的旧更新在重启后被重复处理。
    """
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
