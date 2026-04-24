"""Bot 编排模块 — 组装日志、Bot 实例、Dispatcher 和 Webhook 服务器。"""

from bot.factory import create_bot, create_dispatcher
from bot.server import run_webhook_server
from config import settings
from utils import setup_logging


async def main() -> None:
    """启动 bot 的顶层协程：初始化日志 → 创建 Bot/Dispatcher → 运行 webhook 服务器。"""
    setup_logging(settings.log_level)
    bot = create_bot()
    dp = create_dispatcher()
    await run_webhook_server(bot, dp)
