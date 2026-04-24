"""/help 命令处理器。"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """响应 /help 命令，返回使用简介。"""
    await message.answer("Pejortryia Bot — /start to begin")
