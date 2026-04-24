"""工具模块 — 日志初始化和共享辅助函数。"""

import sys
import logging

# Telegram 超级群组/频道的 chat_id 都小于此阈值（即 -1000000000000）。
# 超过此值的为正数 chat_id（私聊/普通群组），无法通过 t.me 链接访问。
_SUPERGROUP_THRESHOLD = -1000000000000


def setup_logging(level: str = "INFO") -> None:
    """配置控制台日志输出，降低 aiogram 事件日志的噪音。"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


def build_telegram_message_url(chat_id: int | None, message_id: int | None) -> str | None:
    """为超级群组/频道消息构建 t.me 可点击链接，否则返回 None。

    超级群组/频道的 chat_id 格式为 -100XXXXXXXXXX，需去除 "-100" 前缀
    后拼接到 https://t.me/c/ 路径中。普通私聊和群聊无法生成此类链接。
    """
    if not chat_id or not message_id or chat_id > _SUPERGROUP_THRESHOLD:
        return None
    channel_id = str(chat_id)[4:]  # strip "-100" prefix
    return f"https://t.me/c/{channel_id}/{message_id}"
