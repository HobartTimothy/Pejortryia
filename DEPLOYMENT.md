# Pejortryia 部署说明

本文档说明如何在服务器环境中部署并长期运行 Pejortryia（基于 aiogram 3.x + aiohttp 的 Telegram 机器人）。

## 1. 架构

- **入口**: `main.py` → `asyncio.run(bot.main())` → aiohttp 监听端口
- **Webhook 模式**（唯一模式）: 通过 Telegram `set_webhook` 注册，Telegram 推送更新到 `POST {WEBHOOK_PATH}`
- **HTTP 端点**:
  - `POST {WEBHOOK_PATH}` — 接收 Telegram 更新（默认 `/webhook`）
  - `GET /health` — 存活探针，返回 `ok`
  - `GET /hook` — 返回 `{"status": "ok", "message": "配置成功"}`
- **数据**: PostgreSQL 数据库，通过 asyncpg 连接池访问

`WEBHOOK_BASE_URL` 必须为 HTTPS 地址，通常由反向代理（nginx/Caddy）或云负载均衡终止 TLS，转发到应用监听的 `WEBHOOK_HOST:WEBHOOK_PORT`。

### 1.1 访问 URL 说明

Telegram webhook 要求公网可访问的 HTTPS URL。以下是各 URL 的组成与用途：

| 用途 | URL | 说明 |
|------|-----|------|
| **Webhook 接收** | `{WEBHOOK_BASE_URL}{WEBHOOK_PATH}` | Telegram 向此地址 POST 更新。例：`https://bot.example.com/webhook` |
| **健康检查** | `{WEBHOOK_BASE_URL}/health` | 存活探针，返回 `ok`。负载均衡 / 监控告警用 |
| **配置验证** | `{WEBHOOK_BASE_URL}/hook` | 返回 JSON，快速确认 webhook 路径与 TLS 配置正确 |

**URL 拼接规则**：

- `WEBHOOK_BASE_URL` = `https://bot.example.com`（无尾斜杠）
- `WEBHOOK_PATH` = `/webhook`（默认值，以 `/` 开头）
- 完整 webhook URL = `https://bot.example.com/webhook`
- 健康检查 URL = `https://bot.example.com/health`
- 验证 URL = `https://bot.example.com/hook`

**请求流向**（nginx 为例）：

```
Telegram 服务器
    │
    │  POST https://bot.example.com/webhook
    ▼
nginx (443, TLS 终止)
    │
    │  proxy_pass http://127.0.0.1:8080
    ▼
aiohttp 应用 (WEBHOOK_HOST:WEBHOOK_PORT)
    │
    │  SimpleRequestHandler 匹配路径 /webhook
    ▼
aiogram Dispatcher → Router → Handler
```

验证端点可用性：

```bash
# 健康检查
curl -sSf https://bot.example.com/health
# → ok

# 配置验证
curl -sSf https://bot.example.com/hook
# → {"status":"ok","message":"配置成功"}

# 查看 Telegram 侧 webhook 状态
curl -sSf "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
# → {"ok":true,"result":{"url":"https://bot.example.com/webhook",...}}
```

## 2. 环境要求

| 项目 | 要求 |
|------|------|
| Python | **3.14 及以上** |
| 包管理 | [uv](https://github.com/astral-sh/uv)（仓库含 `uv.lock` 锁定版本） |
| 网络 | 公网 HTTPS URL 可达；`api.telegram.org` 出站可达；PostgreSQL 端口可达 |
| 数据库 | PostgreSQL ≥ 14（需提前创建数据库和用户） |

## 3. 获取 Bot Token

1. 在 Telegram 中打开 [@BotFather](https://t.me/BotFather)
2. 创建或使用已有 bot，获取 API Token
3. 切勿将 Token 提交到 Git，仅通过环境变量或 `.env` 注入

## 4. 环境变量

配置通过环境变量或 `.env` 文件加载（pydantic-settings）。

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `BOT_TOKEN` | 是 | Telegram Bot API Token |
| `WEBHOOK_BASE_URL` | 是 | Webhook 的 HTTPS 前缀，不含路径，无尾部 `/`。如 `https://bot.example.com` |
| `WEBHOOK_PATH` | 否 | Webhook 路径，默认 `/webhook` |
| `WEBHOOK_SECRET` | 否 | 与 `set_webhook` 的 `secret_token` 一致，校验失败返回 401 |
| `WEBHOOK_HOST` | 否 | 监听地址，默认 `0.0.0.0` |
| `WEBHOOK_PORT` | 否 | 监听端口，默认 `8080` |
| `LOG_LEVEL` | 否 | 日志级别，默认 `INFO` |
| `ADMIN_IDS` | 否 | 管理员 Telegram 用户 ID，JSON 数组字符串，如 `[123456789]` |
| `DB_HOST` | 否 | PostgreSQL 主机，默认 `localhost` |
| `DB_PORT` | 否 | PostgreSQL 端口，默认 `5432` |
| `DB_USER` | 否 | PostgreSQL 用户名，默认 `pejortryia` |
| `DB_PASSWORD` | 否 | PostgreSQL 密码 |
| `DB_NAME` | 否 | PostgreSQL 数据库名，默认 `pejortryia` |
| `DB_POOL_MIN` | 否 | 连接池最小连接数，默认 `2` |
| `DB_POOL_MAX` | 否 | 连接池最大连接数，默认 `10` |

`.env` 示例：

```env
BOT_TOKEN=123456789:AAbb...
WEBHOOK_BASE_URL=https://bot.example.com
WEBHOOK_PATH=/webhook
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8080
LOG_LEVEL=INFO
ADMIN_IDS=[123456789]
DB_HOST=localhost
DB_PORT=5432
DB_USER=pejortryia
DB_PASSWORD=your-db-password
DB_NAME=pejortryia
```

## 5. 数据库准备

```bash
sudo -u postgres psql -c "CREATE USER pejortryia WITH PASSWORD 'your-db-password';"
sudo -u postgres psql -c "CREATE DATABASE pejortryia OWNER pejortryia;"
```

应用启动时自动建表（`CREATE TABLE IF NOT EXISTS`），无需手动执行 DDL。

## 6. 安装与启动

```bash
# 项目根目录
uv sync
uv run python main.py
```

启动后进程监听 `WEBHOOK_HOST:WEBHOOK_PORT`，并自动向 Telegram 注册 Webhook。验证：

```bash
curl -sSf https://你的域名/health    # 应返回 ok
```

## 7. 生产环境部署

### 7.1 systemd（推荐）

创建服务单元文件，部署目录以 `/opt/pejortryia` 为例：

```ini
[Unit]
Description=Pejortryia Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=bots
Group=bots
WorkingDirectory=/opt/pejortryia
EnvironmentFile=/opt/pejortryia/.env
ExecStart=/usr/bin/uv run python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用：

```bash
sudo cp scripts/deploy/pejortryia.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pejortryia
sudo journalctl -u pejortryia -f
```

### 7.2 反向代理（nginx）

Pejortryia 监听本地端口（默认 `127.0.0.1:8080`），由 nginx 对外提供 HTTPS 并反向代理。

**前置条件**：

- 已拥有域名，DNS 解析到服务器 IP
- 已安装 nginx（建议 ≥ 1.18）

**步骤 1 — 获取 SSL 证书（Let's Encrypt）**：

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书（certbot 自动配置 nginx）
sudo certbot certonly --nginx -d bot.example.com

# 证书路径（certbot 默认）
# 证书: /etc/letsencrypt/live/bot.example.com/fullchain.pem
# 私钥: /etc/letsencrypt/live/bot.example.com/privkey.pem
```

**步骤 2 — 部署 nginx 配置**：

```bash
sudo cp scripts/deploy/nginx.conf.example /etc/nginx/sites-available/pejortryia
sudo ln -s /etc/nginx/sites-available/pejortryia /etc/nginx/sites-enabled/
```

编辑 `/etc/nginx/sites-available/pejortryia`，将 `server_name`、`ssl_certificate`、`ssl_certificate_key`、`proxy_pass` 替换为实际值。

**步骤 3 — 检查并启用的**：

```bash
sudo nginx -t                       # 检查配置语法
sudo systemctl reload nginx         # 重载配置
```

**步骤 4 — 验证**：

```bash
# 从外部访问各端点
curl -sSf https://bot.example.com/health   # → ok
curl -sSf https://bot.example.com/hook     # → {"status":"ok","message":"配置成功"}

# 确认 Telegram webhook 已注册
curl -sSf "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
# → "url" 应为 https://bot.example.com/webhook
```

完整配置模板见 `scripts/deploy/nginx.conf.example`，包含 HTTP→HTTPS 重定向、ACME 验证路径、TLS 最佳实践、代理超时等。

### 7.3 Docker

```dockerfile
FROM python:3.14-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev
COPY . .
ENV WEBHOOK_HOST=0.0.0.0 WEBHOOK_PORT=8080
EXPOSE 8080
CMD ["uv", "run", "python", "main.py"]
```

## 8. 发布流程

1. 拉取新版本: `git pull`
2. 同步依赖: `uv sync`
3. 重启进程: `sudo systemctl restart pejortryia`
4. 检查日志: `sudo journalctl -u pejortryia -f`

## 9. 故障排查

| 现象 | 可能原因 |
|------|----------|
| 启动即退出 | `BOT_TOKEN` 或 `WEBHOOK_BASE_URL` 未设置 / `.env` 路径不对 |
| `WEBHOOK_BASE_URL` 校验失败 | 未以 `https://` 开头 |
| Webhook 不工作 | 反向代理未转发 POST；`WEBHOOK_PATH` 不一致；`WEBHOOK_SECRET` 不匹配 |
| 健康检查失败 | 探针端口与 `WEBHOOK_PORT` 不一致；nginx 未放行 |
| 书签丢失 | PostgreSQL 数据未备份或库/用户被删除 |
| 数据库连接失败 | `DB_HOST`/`DB_PORT` 不可达；用户名密码错误；数据库不存在 |

## 10. 安全建议

- `.env` 不要提交到 Git
- 设置 `WEBHOOK_SECRET` 防止伪造更新请求
- 限制文件系统权限，仅运行用户可读写项目目录
- nginx 侧可配置 `client_max_body_size` 限制请求体大小
