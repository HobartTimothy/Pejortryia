"""日志中间件 — 记录每条 Update 的类型和处理耗时。"""

import logging
import time
from collections.abc import Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

# aiogram 中间件 handler 签名
type MiddlewareHandler = Callable[[TelegramObject, dict[str, object]], Awaitable[None]]


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: MiddlewareHandler,
        event: TelegramObject,
        data: dict[str, object],
    ) -> None:
        start = time.perf_counter()
        logger.info("Update received: %s", type(event).__name__)
        await handler(event, data)
        elapsed = time.perf_counter() - start
        logger.info("Update processed in %.3fs", elapsed)
