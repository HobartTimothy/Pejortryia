"""Pejortryia — Telegram bot 入口模块。

命令行 `python main.py` 或 `uv run python main.py` 启动。
"""

import asyncio

from bot import main as bot_main


def main() -> None:
    """同步入口：启动 asyncio 事件循环并运行 bot。"""
    asyncio.run(bot_main())


if __name__ == "__main__":
    main()
