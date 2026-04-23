from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()  # 每个路由文件创建独立 Router，最终在 bot.py 中注册


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """处理 /help 命令 — 展示简易帮助信息。"""
    await message.answer("Pejortryia Bot — /start to begin")
