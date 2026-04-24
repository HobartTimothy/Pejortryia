from __future__ import annotations

import logging

from aiogram import Router, F, Bot
from aiogram.enums import MessageOriginType
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from keyboards.bookmark import (
    PAGE_SIZE,
    BookmarkDelete,
    BookmarkDetail,
    BookmarkList,
    build_detail_keyboard,
    build_list_keyboard,
)
from services.database import (
    add_bookmark,
    count_bookmarks,
    delete_bookmark,
    get_bookmark,
    list_bookmarks,
)

logger = logging.getLogger(__name__)

router = Router()


def _extract_origin_info(message: Message) -> dict:
    origin = message.forward_origin
    if origin is None:
        return {
            "source_type": "direct",
            "source_name": None,
            "chat_id": message.chat.id,
            "message_id": message.message_id,
        }

    if origin.type == MessageOriginType.USER:
        return {
            "source_type": "forward_user",
            "source_name": origin.sender_user.full_name,
            "chat_id": None,
            "message_id": None,
        }
    if origin.type == MessageOriginType.HIDDEN_USER:
        return {
            "source_type": "forward_hidden",
            "source_name": origin.sender_user_name,
            "chat_id": None,
            "message_id": None,
        }
    if origin.type == MessageOriginType.CHAT:
        return {
            "source_type": "forward_chat",
            "source_name": origin.sender_chat.title,
            "chat_id": origin.sender_chat.id,
            "message_id": None,
        }
    if origin.type == MessageOriginType.CHANNEL:
        return {
            "source_type": "forward_channel",
            "source_name": origin.chat.title,
            "chat_id": origin.chat.id,
            "message_id": origin.message_id,
        }

    return {"source_type": "unknown", "source_name": None, "chat_id": None, "message_id": None}


def _extract_content_info(message: Message) -> dict:
    if message.text:
        return {"msg_type": "text", "summary": message.text, "file_id": None}
    if message.photo:
        return {"msg_type": "photo", "summary": message.caption, "file_id": message.photo[-1].file_id}
    if message.document:
        return {
            "msg_type": "document",
            "summary": message.caption or message.document.file_name,
            "file_id": message.document.file_id,
        }
    if message.video:
        return {"msg_type": "video", "summary": message.caption, "file_id": message.video.file_id}
    if message.audio:
        title = " - ".join(filter(None, [message.audio.performer, message.audio.title]))
        return {"msg_type": "audio", "summary": message.caption or title, "file_id": message.audio.file_id}
    if message.voice:
        return {"msg_type": "voice", "summary": "[语音消息]", "file_id": message.voice.file_id}
    if message.animation:
        return {"msg_type": "animation", "summary": message.caption, "file_id": message.animation.file_id}
    return {"msg_type": "unknown", "summary": None, "file_id": None}


async def _save_bookmark(message: Message) -> None:
    content = _extract_content_info(message)
    origin = _extract_origin_info(message)
    await add_bookmark(
        user_id=message.from_user.id,
        msg_type=content["msg_type"],
        summary=content["summary"],
        file_id=content["file_id"],
        chat_id=origin["chat_id"],
        message_id=origin["message_id"],
        source_type=origin["source_type"],
        source_name=origin["source_name"],
    )
    await message.answer("✅ 已收藏")


async def _render_list_page(user_id: int, page: int) -> tuple[str, InlineKeyboardMarkup | None]:
    total = await count_bookmarks(user_id)
    if total == 0:
        return "📚 收藏夹为空\n\n转发或直接发送消息给我就可收藏！", None

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages - 1)
    bookmarks = await list_bookmarks(user_id, page)
    text = f"📚 我的收藏（共 {total} 条）\n\n"
    for i, bm in enumerate(bookmarks, start=page * PAGE_SIZE + 1):
        source = f" · 来自 {bm['source_name']}" if bm.get("source_name") else ""
        summary = (bm.get("summary") or f"[{bm['msg_type']}]")[:40]
        text += f"{i}. {summary}{source}\n"

    markup = build_list_keyboard(bookmarks, page, total_pages)
    return text, markup


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    text, markup = await _render_list_page(message.from_user.id, page=0)
    await message.answer(text, reply_markup=markup)


@router.message(F.photo | F.document | F.video | F.audio | F.voice | F.animation)
async def on_save_media(message: Message) -> None:
    await _save_bookmark(message)


@router.message(F.text, ~F.text.startswith("/"))
async def on_save_text(message: Message) -> None:
    await _save_bookmark(message)


@router.callback_query(BookmarkList.filter())
async def on_list_page(query: CallbackQuery, callback_data: BookmarkList) -> None:
    text, markup = await _render_list_page(query.from_user.id, page=callback_data.page)
    try:
        await query.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await query.message.answer(text, reply_markup=markup)
    await query.answer()


@router.callback_query(BookmarkDetail.filter())
async def on_bookmark_detail(query: CallbackQuery, callback_data: BookmarkDetail, bot: Bot) -> None:
    user_id = query.from_user.id
    bm = await get_bookmark(user_id, callback_data.id)
    if bm is None:
        await query.answer("收藏不存在", show_alert=True)
        return

    source_line = ""
    if bm.get("source_name"):
        source_line = f"\n📍 来自: {bm['source_name']}"
    if bm.get("source_type") == "forward_channel" and bm.get("chat_id") and bm.get("message_id"):
        channel_id = str(bm["chat_id"])[4:]
        source_line += f"\n🔗 原文: https://t.me/c/{channel_id}/{bm['message_id']}"

    detail_markup = build_detail_keyboard(
        bookmark_id=bm["id"],
        page=callback_data.page,
        chat_id=bm.get("chat_id"),
        message_id=bm.get("message_id"),
    )

    if bm["file_id"]:
        send_method = {
            "photo": bot.send_photo,
            "document": bot.send_document,
            "video": bot.send_video,
            "audio": bot.send_audio,
            "voice": bot.send_voice,
            "animation": bot.send_animation,
        }.get(bm["msg_type"], bot.send_document)

        caption = (bm.get("summary") or "") + source_line
        if len(caption) > 1024:
            caption = caption[:1021] + "..."

        try:
            await send_method(
                chat_id=query.message.chat.id,
                file_id=bm["file_id"],
                caption=caption,
                reply_markup=detail_markup,
            )
        except TelegramBadRequest:
            await query.message.answer(f"⚠️ 媒体文件已过期{source_line}", reply_markup=detail_markup)
    else:
        await query.message.answer(f"{bm.get('summary', '')}{source_line}", reply_markup=detail_markup)

    await query.answer()


@router.callback_query(BookmarkDelete.filter())
async def on_bookmark_delete(query: CallbackQuery, callback_data: BookmarkDelete) -> None:
    deleted = await delete_bookmark(query.from_user.id, callback_data.id)
    if deleted:
        try:
            await query.message.edit_text("🗑️ 此收藏已删除")
        except TelegramBadRequest:
            await query.message.answer("🗑️ 此收藏已删除")
    else:
        await query.answer("收藏不存在", show_alert=True)
        return
    await query.answer()
