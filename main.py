import asyncio

from bot import main as bot_main


def main() -> None:
    """项目入口：启动异步事件循环并运行 bot。"""
    asyncio.run(bot_main())


if __name__ == "__main__":
    main()
