import logging
import time
from collections.abc import Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

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
