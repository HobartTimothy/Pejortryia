# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pejortryia is a Telegram bot framework built on aiogram 3.x with Python 3.14+, webhook mode only.

## Commands

- **Install deps:** `uv sync`
- **Run bot:** `uv run python main.py` (requires `.env` with `BOT_TOKEN` + `WEBHOOK_BASE_URL`)
- **Lint:** `uv run ruff check .`
- **Format:** `uv run ruff format .`

## Architecture

```
main.py              → entry point, calls bot.main()
bot/
    __init__.py      → main() — orchestrator: logging → bot/dispatcher → server
    factory.py       → create_bot() + create_dispatcher()
    server.py        → run_webhook_server() — aiohttp app, routes, webhook setup
config.py            → pydantic-settings (BOT_TOKEN, DB_*, WEBHOOK_*, ...)
handlers/            → aiogram Router per file, registered in bot.factory via dp.include_router()
keyboards/           → keyboard builders
middleware.py        → LoggingMiddleware, registered on Dispatcher
services/            → business logic (database via asyncpg pool)
utils.py             → logging configuration + shared helpers (URL builder)
```

- Config is validated at import time — missing `BOT_TOKEN` or `WEBHOOK_BASE_URL` fails immediately
- Webhook mode is the only mode — requires `BOT_TOKEN` + `WEBHOOK_BASE_URL` (HTTPS)
- Each handler creates its own `Router()` instance; `handlers/__init__.py` re-exports them
- New feature: create handler file → re-export in `handlers/__init__.py` → `dp.include_router()` in `bot/factory.py`
- Default parse mode is HTML (`ParseMode.HTML`)
- HTTP endpoints: `GET /health` → `"ok"`, `GET /hook` → `{"status": "ok", "message": "配置成功"}`

## Environment

Required: `BOT_TOKEN`, `WEBHOOK_BASE_URL` (HTTPS prefix, no trailing slash). Optional: `WEBHOOK_PATH`, `WEBHOOK_SECRET`, `WEBHOOK_HOST`, `WEBHOOK_PORT`, `LOG_LEVEL`, `ADMIN_IDS`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_POOL_MIN`, `DB_POOL_MAX`. See `.env`.
