from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()  # 每个路由文件创建独立 Router，最终在 bot.py 中注册


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """处理 /start 命令 — 用户首次交互或重新开始的入口。"""
    await message.answer("Hello! Pejortryia is running.")
