"""/start 命令处理器。"""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """响应 /start 命令，返回 bot 上线提示。"""
    await message.answer("Hello! Pejortryia is running.")
