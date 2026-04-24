from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

PAGE_SIZE = 5

MSG_TYPE_LABELS: dict[str, str] = {
    "text": "📝",
    "photo": "🖼️",
    "document": "📎",
    "video": "🎬",
    "audio": "🎵",
    "voice": "🎤",
    "animation": "🎞️",
}


class BookmarkList(CallbackData, prefix="bm_ls"):
    page: int


class BookmarkDetail(CallbackData, prefix="bm_dt"):
    id: int
    page: int


class BookmarkDelete(CallbackData, prefix="bm_dl"):
    id: int
    page: int


def _build_original_url(chat_id: int, message_id: int) -> str | None:
    if chat_id > -1000000000000:
        return None
    channel_id = str(chat_id)[4:]
    return f"https://t.me/c/{channel_id}/{message_id}"


def build_list_keyboard(
    bookmarks: list[dict],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for bm in bookmarks:
        label = _format_bookmark_label(bm)
        builder.button(
            text=label,
            callback_data=BookmarkDetail(id=bm["id"], page=page),
        )

    nav_buttons: list[InlineKeyboardButton] = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀ 上一页", callback_data=BookmarkList(page=page - 1).pack()))
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=BookmarkList(page=page).pack())
    )
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="下一页 ▶", callback_data=BookmarkList(page=page + 1).pack()))

    builder.row(*nav_buttons)
    builder.adjust(1)

    return builder.as_markup()


def build_detail_keyboard(
    bookmark_id: int,
    page: int,
    chat_id: int | None = None,
    message_id: int | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    url = _build_original_url(chat_id, message_id) if chat_id and message_id else None
    if url:
        builder.button(text="🔗 查看原文", url=url)

    builder.button(text="🗑️ 删除", callback_data=BookmarkDelete(id=bookmark_id, page=page))
    builder.button(text="↩️ 返回列表", callback_data=BookmarkList(page=page))
    builder.adjust(2 if url else 1)

    return builder.as_markup()


def _format_bookmark_label(bm: dict) -> str:
    icon = MSG_TYPE_LABELS.get(bm["msg_type"], "📌")
    summary = bm.get("summary") or ""
    truncated = summary[:30] + ("..." if len(summary) > 30 else "")
    if not truncated:
        truncated = f"[{bm['msg_type']}]"
    return f"{icon} {truncated}"
