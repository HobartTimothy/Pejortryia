import logging
import time
from collections.abc import Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

# PEP 695 类型别名：中间件链中下一个处理器的签名
type MiddlewareHandler = Callable[[TelegramObject, dict[str, object]], Awaitable[None]]


class LoggingMiddleware(BaseMiddleware):
    """外层日志中间件：记录每个 Update 的接收与处理耗时。"""

    async def __call__(
        self,
        handler: MiddlewareHandler,  # 链中的下一个处理器
        event: TelegramObject,  # 当前 Telegram 事件（Message / CallbackQuery 等）
        data: dict[str, object],  # 上下文数据，传递给后续处理器
    ) -> None:
        start = time.perf_counter()
        logger.info("Update received: %s", type(event).__name__)
        await handler(event, data)  # 继续处理链
        elapsed = time.perf_counter() - start
        logger.info("Update processed in %.3fs", elapsed)
