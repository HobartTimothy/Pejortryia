# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pejortryia is a Telegram bot framework built on aiogram 3.x with Python 3.14+.

## Commands

- **Install deps:** `uv sync`
- **Run bot:** `uv run python main.py` (requires `.env` with `BOT_TOKEN`)
- **Lint:** `uv run ruff check .`
- **Format:** `uv run ruff format .`

## Architecture

```
main.py              → entry point, calls bot.main()
bot.py               → Bot + Dispatcher assembly, start_polling
config/settings.py   → pydantic-settings (BOT_TOKEN, LOG_LEVEL, ADMIN_IDS)
routers/             → aiogram Router per file, registered in bot.py via dp.include_router()
middleware/          → BaseMiddleware subclasses, registered on Dispatcher
keyboards/           → keyboard builders (stub)
filters/             → custom filters (stub)
services/            → business logic (stub)
utils/logging.py     → logging configuration
```

- Config is validated at import time — missing `BOT_TOKEN` fails immediately
- Each router creates its own `Router()` instance; `routers/__init__.py` re-exports them
- New feature: create router file → re-export in `routers/__init__.py` → `dp.include_router()` in `bot.py`
- Default parse mode is HTML (`ParseMode.HTML`)

## Environment

Copy `.env.example` to `.env` and set `BOT_TOKEN`.
