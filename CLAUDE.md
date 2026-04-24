# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pejortryia is a Telegram bot framework built on aiogram 3.x with Python 3.14+.

## Commands

- **Install deps:** `uv sync`
- **Run bot:** `uv run python main.py` (requires `.env` with `BOT_TOKEN`; set `WEBHOOK_BASE_URL` for webhook mode)
- **Lint:** `uv run ruff check .`
- **Format:** `uv run ruff format .`

## Architecture

```
main.py              → entry point, calls bot.main()
bot/
    __init__.py      → main() — mode selector (polling vs webhook)
    _factory.py      → create_bot() + create_dispatcher() (shared)
    polling.py       → run_polling() — asyncio long-polling
    webhook.py       → run_webhook() — aiohttp webhook server
config/settings.py   → pydantic-settings (BOT_TOKEN, WEBHOOK_*, LOG_LEVEL, ADMIN_IDS)
routers/             → aiogram Router per file, registered in bot._factory via dp.include_router()
middleware/          → BaseMiddleware subclasses, registered on Dispatcher
keyboards/           → keyboard builders
filters/             → custom filters (stub)
services/            → business logic (database)
utils/logging.py     → logging configuration
```

- Config is validated at import time — missing `BOT_TOKEN` fails immediately
- **Mode selection**: `WEBHOOK_BASE_URL` set → webhook mode; unset/empty → polling mode
- Polling mode needs only `BOT_TOKEN` — ideal for local development
- Webhook mode needs `BOT_TOKEN` + `WEBHOOK_BASE_URL` (HTTPS) — for production
- Each router creates its own `Router()` instance; `routers/__init__.py` re-exports them
- New feature: create router file → re-export in `routers/__init__.py` → `dp.include_router()` in `bot/_factory.py`
- Default parse mode is HTML (`ParseMode.HTML`)

## Environment

Set `BOT_TOKEN` (required). Set `WEBHOOK_BASE_URL` (HTTPS prefix, no trailing slash) for webhook mode; leave empty for polling mode. Optional: `WEBHOOK_PATH` / `WEBHOOK_SECRET` / `WEBHOOK_HOST` / `WEBHOOK_PORT` (webhook only), `LOG_LEVEL`, `ADMIN_IDS`. See `.env.example`.
