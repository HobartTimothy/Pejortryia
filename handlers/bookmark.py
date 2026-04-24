"""收藏功能的命令和消息处理器。

支持以下操作：
- /list — 分页查看收藏列表
- 直接发送文本或媒体消息 — 自动收藏
- 收藏列表翻页、查看详情、删除（通过内联按钮回调）
"""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.enums import MessageOriginType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

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
from utils import build_telegram_message_url

router = Router()


def _extract_origin_info(message: Message) -> dict:
    """从消息的 forward_origin 提取来源信息，用于标注收藏来源。

    直接发送的消息标记为 "direct"；转发消息根据 origin.type
    区分用户转发、隐藏用户转发、群聊转发、频道转发等类型。
    """
    origin = message.forward_origin
    if origin is None:
        return {
            "source_type": "direct",
            "source_name": None,
            "chat_id": message.chat.id,
            "message_id": message.message_id,
        }

    match origin.type:
        case MessageOriginType.USER:
            return {
                "source_type": "forward_user",
                "source_name": origin.sender_user.full_name,
                "chat_id": None,
                "message_id": None,
            }
        case MessageOriginType.HIDDEN_USER:
            return {
                "source_type": "forward_hidden",
                "source_name": origin.sender_user_name,
                "chat_id": None,
                "message_id": None,
            }
        case MessageOriginType.CHAT:
            return {
                "source_type": "forward_chat",
                "source_name": origin.sender_chat.title,
                "chat_id": origin.sender_chat.id,
                "message_id": None,
            }
        case MessageOriginType.CHANNEL:
            return {
                "source_type": "forward_channel",
                "source_name": origin.chat.title,
                "chat_id": origin.chat.id,
                "message_id": origin.message_id,
            }
        case _:
            return {"source_type": "unknown", "source_name": None, "chat_id": None, "message_id": None}


def _extract_content_info(message: Message) -> dict:
    """从消息中提取内容摘要和 file_id，按消息类型分别处理。

    - text: 直接取全文
    - photo: 取最后一张（最高分辨率）的 file_id，caption 作为摘要
    - audio: 格式化为 "演唱者 - 曲名"
    - voice: 无文本，用占位符 "[语音消息]"
    返回值包含 msg_type、summary（可为 None）、file_id（可为 None）。
    """
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
    """提取消息内容和来源信息，写入数据库并回复确认。"""
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
    """渲染收藏列表文本和对应页的内联键盘。

    返回 (文本, 键盘) 元组；收藏夹为空时键盘为 None。
    """
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


# =========================================================================
# 命令和消息处理器
# =========================================================================


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    """/list — 显示收藏列表第一页。"""
    text, markup = await _render_list_page(message.from_user.id, page=0)
    await message.answer(text, reply_markup=markup)


@router.message(F.photo | F.document | F.video | F.audio | F.voice | F.animation)
async def on_save_media(message: Message) -> None:
    """收到媒体消息时自动收藏。"""
    await _save_bookmark(message)


@router.message(F.text, ~F.text.startswith("/"))
async def on_save_text(message: Message) -> None:
    """收到非命令文本消息时自动收藏（排除以 "/" 开头的命令）。"""
    await _save_bookmark(message)


# =========================================================================
# 内联按钮回调处理器
# =========================================================================


@router.callback_query(BookmarkList.filter())
async def on_list_page(query: CallbackQuery, callback_data: BookmarkList) -> None:
    """翻页按钮回调：渲染指定页的收藏列表。

    优先尝试编辑原消息以保持对话整洁；编辑失败时（如消息已删除）发送新消息。
    """
    text, markup = await _render_list_page(query.from_user.id, page=callback_data.page)
    try:
        await query.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await query.message.answer(text, reply_markup=markup)
    await query.answer()


@router.callback_query(BookmarkDetail.filter())
async def on_bookmark_detail(query: CallbackQuery, callback_data: BookmarkDetail, bot: Bot) -> None:
    """查看收藏详情：显示内容、来源信息、原文链接，并提供删除/返回操作。

    有 file_id 的媒体收藏尝试通过 Bot 方法重新发送（如 send_photo）；
    媒体文件可能在 Telegram 服务器上已过期，此时回退为纯文本提示。
    caption 长度限制在 1024 字符以内，超出截断。
    """
    user_id = query.from_user.id
    bm = await get_bookmark(user_id, callback_data.id)
    if bm is None:
        await query.answer("收藏不存在", show_alert=True)
        return

    source_line = ""
    if bm.get("source_name"):
        source_line = f"\n📍 来自: {bm['source_name']}"
    url = build_telegram_message_url(bm.get("chat_id"), bm.get("message_id"))
    if url:
        source_line += f"\n🔗 原文: {url}"

    detail_markup = build_detail_keyboard(
        bookmark_id=bm["id"],
        page=callback_data.page,
        chat_id=bm.get("chat_id"),
        message_id=bm.get("message_id"),
    )

    if bm["file_id"]:
        # 媒体消息：按类型选择对应的 Bot.send_* 方法重新发送
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
    """删除收藏：校验用户所有权后删除，编辑原消息为删除确认。

    优先尝试编辑原消息；编辑失败（如消息来自其他用户）则发送新消息。
    """
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
