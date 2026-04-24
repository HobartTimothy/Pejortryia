"""收藏功能的键盘构建模块。

包含 InlineKeyboard 构建函数和 CallbackData 工厂类。
列表键盘使用 InlineKeyboardBuilder，分页导航通过回调数据传递页码。
"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils import build_telegram_message_url

PAGE_SIZE = 5

# 消息类型 → 列表项图标映射
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
    """列表翻页回调，携带目标页码。"""

    page: int


class BookmarkDetail(CallbackData, prefix="bm_dt"):
    """查看收藏详情回调，携带收藏 ID 和返回页码。"""

    id: int
    page: int


class BookmarkDelete(CallbackData, prefix="bm_dl"):
    """删除收藏回调，携带收藏 ID 和返回页码。"""

    id: int
    page: int


def build_list_keyboard(
    bookmarks: list[dict],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """构建收藏列表内联键盘：每条收藏一行按钮 + 底部翻页导航栏。"""
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
    """构建收藏详情内联键盘：可查看原文链接（如适用）、删除、返回列表。"""
    builder = InlineKeyboardBuilder()

    url = build_telegram_message_url(chat_id, message_id)
    if url:
        builder.button(text="🔗 查看原文", url=url)

    builder.button(text="🗑️ 删除", callback_data=BookmarkDelete(id=bookmark_id, page=page))
    builder.button(text="↩️ 返回列表", callback_data=BookmarkList(page=page))
    builder.adjust(2 if url else 1)

    return builder.as_markup()


def _format_bookmark_label(bm: dict) -> str:
    """格式化收藏列表项文本：图标 + 摘要（截断至 30 字符）。"""
    icon = MSG_TYPE_LABELS.get(bm["msg_type"], "📌")
    summary = bm.get("summary") or ""
    truncated = summary[:30] + ("..." if len(summary) > 30 else "")
    if not truncated:
        truncated = f"[{bm['msg_type']}]"
    return f"{icon} {truncated}"
