# Pejortryia 部署说明

本文档说明如何在服务器或本机环境中部署并长期运行 **Pejortryia**（基于 aiogram 3.x 的 Telegram 机器人）。

## 1. 架构与运行方式

- **入口**：`main.py` → 同步调用 `bot.main()`，内部根据配置选择运行模式。
- **与 Telegram 通信**：支持 **Webhook** 和 **长轮询（Polling）** 两种模式。当 `WEBHOOK_BASE_URL` 已配置时使用 Webhook；未配置时使用 Polling（无需公网 HTTPS，适合本地开发）。
  - **Webhook 模式**：进程需 **入站**：Telegram 能通过公网 **HTTPS** 访问你配置的 Webhook URL；需 **出站**：本进程调用 `api.telegram.org`（`set_webhook` / Bot API）。
  - **Polling 模式**：仅需 **出站** 访问 `api.telegram.org`，无需公网 HTTPS。
- **HTTP**：
  - `POST {WEBHOOK_PATH}`：由 Telegram 推送更新（默认路径 `/webhook`，与 `WEBHOOK_BASE_URL` 拼接为完整 URL）。
  - `GET /health`：存活探针，返回纯文本 `ok`（供负载均衡 / SAE 健康检查使用）。
- **数据**：SQLite 数据库文件默认位于项目根目录下的 `bookmarks.db`，与代码同级；部署时需保证该路径可写且**随备份保留**，否则书签数据会丢失。

**`WEBHOOK_BASE_URL`** 须为 Telegram 可验证的 **HTTPS** 地址（生产环境），且路径与 `WEBHOOK_PATH` 一致；前面通常需反向代理或云负载均衡终止 TLS，并将请求转发到应用监听的 `WEBHOOK_HOST`:`WEBHOOK_PORT`。

## 2. 环境要求

| 项目 | 要求 |
|------|------|
| Python | **3.14 及以上**（见 `pyproject.toml` 中 `requires-python`） |
| 包管理 | 推荐使用 [uv](https://github.com/astral-sh/uv)（与仓库内 `uv.lock` 锁定版本一致） |
| 网络 | 公网 **HTTPS** Webhook URL；实例可访问 `api.telegram.org`（出站） |

## 3. 获取 Bot Token

1. 在 Telegram 中打开 [@BotFather](https://t.me/BotFather)。
2. 创建新 bot 或使用已有 bot，获取 **API Token**（形如 `123456:ABC-DEF...`）。
3. 切勿将 Token 提交到 Git；仅通过环境变量或服务器上的 `.env` 注入。

## 4. 环境变量

配置通过 **环境变量** 或项目根目录下的 **`.env`** 文件加载（`config/settings.py` 使用 pydantic-settings）。

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `BOT_TOKEN` | 是 | Telegram Bot API Token |
| `WEBHOOK_BASE_URL` | 否 | Webhook 的 **HTTPS** 前缀，**不含** 路径、**无** 尾部 `/`。例如 `https://bot.example.com`；须与对外暴露域名一致。**设置此值启用 Webhook 模式；不设则使用 Polling 模式（无需公网 HTTPS，适合本地开发）** |
| `WEBHOOK_PATH` | 否 | Webhook 路径，默认 `/webhook`；与 `WEBHOOK_BASE_URL` 拼接后须等于在 Telegram 登记的 URL |
| `WEBHOOK_SECRET` | 否 | 若设置，须与 `set_webhook` 的 `secret_token` 一致；请求头 `X-Telegram-Bot-Api-Secret-Token` 校验失败将返回 401 |
| `WEBHOOK_HOST` | 否 | 监听地址，默认 `0.0.0.0` |
| `WEBHOOK_PORT` | 否 | 监听端口，默认 `8080`（与 SLB / 容器端口一致） |
| `LOG_LEVEL` | 否 | 日志级别，默认 `INFO`（如 `DEBUG`、`WARNING`） |
| `ADMIN_IDS` | 否 | 管理员 Telegram 用户 ID 列表，须为 **JSON 数组** 字符串（pydantic-settings 按 JSON 解析），例如 `[123456789]` 或 `[123456789,987654321]`；未设置则为空列表 |

**`.env` 示例**（勿提交到 Git）：

```env
BOT_TOKEN=123456789:AAbb...
WEBHOOK_BASE_URL=https://bot.example.com
WEBHOOK_PATH=/webhook
# WEBHOOK_SECRET=your-long-random-secret
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8080
LOG_LEVEL=INFO
ADMIN_IDS=[123456789,987654321]
```

**注意**：应用目录下需存在可读的 `.env`（若使用文件方式），或直接在进程管理器 / 容器中设置上述环境变量。若 shell 里导出含方括号的变量，注意按所用 shell 的引号规则转义。

## 5. 安装依赖

在**项目根目录**（含 `pyproject.toml`、`uv.lock`）执行：

```bash
uv sync
```

仅安装生产依赖；开发依赖（如 `ruff`）在默认 `uv sync` 中可按需省略或单独使用 `uv sync --group dev`。

## 6. 启动与验证

```bash
# Polling 模式（本地开发，仅需 BOT_TOKEN）：
uv run python main.py

# Webhook 模式（生产环境，需设置 WEBHOOK_BASE_URL）：
uv run python main.py
```

启动成功后进程监听 `WEBHOOK_HOST:WEBHOOK_PORT`，并在启动时向 Telegram 注册 Webhook。确认对外 HTTPS URL 可达后，在 Bot 中发送 `/start` 等命令做功能验证。可用 `curl -sSf https://你的域名/health` 检查存活。

停止：在终端中 `Ctrl+C`；生产环境请使用下文进程管理方式优雅退出，以便关闭数据库连接。

## 7. 生产环境建议

### 7.1 工作目录与权限

- 将代码部署到固定目录（例如 `/opt/pejortryia`）。
- 运行用户对项目目录有读权限，对 **`bookmarks.db` 所在目录** 有写权限。
- 首次运行会自动创建 `bookmarks.db`；若从旧环境迁移，请一并复制该文件。

### 7.2 使用 systemd（Linux 常见做法）

示例单元文件 `/etc/systemd/system/pejortryia.service`（请按实际用户与路径修改）：

```ini
[Unit]
Description=Pejortryia Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pejortryia
Group=pejortryia
WorkingDirectory=/opt/pejortryia
EnvironmentFile=/opt/pejortryia/.env
ExecStart=/home/pejortryia/.local/bin/uv run python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

说明：

- `EnvironmentFile` 指向仅包含 `KEY=value` 的 `.env`（不要提交到版本库）。
- `ExecStart` 中的 `uv` 路径可用 `which uv` 在部署用户下确认；若使用系统级安装，改为绝对路径即可。

启用并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pejortryia
sudo journalctl -u pejortryia -f
```

### 7.3 其他守护方式

- **supervisord**：将 `uv run python main.py` 作为 `command`，`directory` 设为项目根目录，并配置环境变量或 `environment` 段。
- **Windows 服务 / 任务计划**：保证开机或登录后在工作目录下执行同一命令，并设置系统环境变量或 `.env`。

核心原则：**固定工作目录**、**正确注入 `BOT_TOKEN` 与 `WEBHOOK_BASE_URL`（及可选 `WEBHOOK_SECRET`）**、**公网 HTTPS 与反向代理配置正确**、**持久化 `bookmarks.db`**。

## 8. 运维与发布流程（简要）

1. 拉取新版本代码到部署目录。
2. 执行 `uv sync` 同步依赖（若 `uv.lock` 有更新）。
3. 重启进程（如 `systemctl restart pejortryia`）。
4. 观察日志确认无报错。

## 9. 故障排查

| 现象 | 可能原因 |
|------|----------|
| 启动即退出并提示缺少配置 | 未设置 `BOT_TOKEN` 或 `.env` 路径不对 |
| 无法连接 Telegram / Webhook 无更新 | 出站被拦；`WEBHOOK_BASE_URL` 非 HTTPS 或路径与控制台不一致；反向代理未转发 `POST` 到 `WEBHOOK_PATH`；`WEBHOOK_SECRET` 与 BotFather/环境不一致 |
| 健康检查失败 | 探针应请求 **`GET /health`**（或放行该路径），端口与 `WEBHOOK_PORT` 一致 |
| 书签丢失 | `bookmarks.db` 未随部署目录备份或工作目录被改到无旧库的路径 |
| 权限错误 | 运行用户对 `bookmarks.db` 或项目目录无写权限 |

本地可先用 `uv run ruff check .` 做静态检查（需安装 dev 依赖组）。

## 10. 阿里云 SAE（ZIP 包部署 Python）

本节在官方流程基础上，说明如何把 **Pejortryia** 打成符合 SAE 要求的 ZIP 并配置运行。完整控制台步骤与参数释义请以阿里云文档为准：[在 SAE 控制台以 ZIP 包方式部署 Python 应用](https://help.aliyun.com/zh/sae/deploy-a-python-application-using-a-zip-package)。

### 10.1 与官方 Web 示例的差异

Pejortryia 使用 **aiohttp** 直接监听端口（默认 `8080`），提供 **`GET /health`** 与 **`POST {WEBHOOK_PATH}`**，与官方用 gunicorn 托管 WSGI 的示例不同，但同样需在 SAE 上暴露 **容器端口**（与 `WEBHOOK_PORT` 一致），并由 **CLB / 网关** 提供 **HTTPS**，域名与 `WEBHOOK_BASE_URL` 一致。

启动命令示例：

```text
python main.py
```

若运行环境将解释器固定为 `python3`，则改为 `python3 main.py`（以 SAE 所选 Python 技术栈说明为准）。**无需**强行改用 gunicorn，除非自行封装 ASGI/HTTP 服务器。

### 10.2 准备部署包（脚本，推荐）

仓库提供打包脚本，在**仓库根目录**执行：

```bash
uv run python scripts/sae/build_zip.py
# 可选：-o dist/sae/pejortryia-sae.zip；依赖安装失败时可加 --no-hashes
```

Windows：`.\scripts\sae\build_zip.ps1`；Linux / macOS：`./scripts/sae/build_zip.sh`（需 `chmod +x`）。

默认输出：`dist/sae/pejortryia-sae-<UTC时间>.zip`。手动打包时亦可按 [Python 代码包要求](https://help.aliyun.com/zh/sae/create-sae-compatible-packages#6d72bc5ef3l5v) 在根目录放置 `uv export` 生成的 `requirements.txt` 后打 ZIP。勿将 `.env`、`bookmarks.db` 打入制品。

### 10.3 控制台部署要点（代码包 / Python）

| 配置项 | 建议 |
|--------|------|
| **技术栈 / Python 版本** | 选择与代码兼容的版本。当前 `pyproject.toml` 要求 **Python ≥ 3.14**；若 SAE 暂无 3.14，需自行降级并回归测试。 |
| **启动命令** | `python main.py`（或 `python3 main.py`）。 |
| **端口 / 访问** | 应用监听 `WEBHOOK_PORT`（默认 8080）；绑定 CLB / 网关，对外 **HTTPS**；`WEBHOOK_BASE_URL` 填该 HTTPS 根地址（无尾斜杠）。 |
| **依赖** | 根目录 `requirements.txt`（或由打包脚本生成）。 |
| **环境变量** | 至少 `BOT_TOKEN`、`WEBHOOK_BASE_URL`；建议配置 `WEBHOOK_PATH`、`WEBHOOK_PORT`；可选 `WEBHOOK_SECRET`、`LOG_LEVEL`、`ADMIN_IDS`（JSON 数组）。 |
| **出网** | 需访问 `api.telegram.org`（`set_webhook` 等）；按需配置 NAT / EIP。 |
| **数据持久化** | `bookmarks.db` 建议挂载 NAS 等，见第 1 节。 |

### 10.4 健康检查与发布

健康检查可配置为 **`GET /health`**（HTTP 200，响应体 `ok`），端口与 `WEBHOOK_PORT` 一致。发布新版本：更新 ZIP → 部署 → 查看变更记录与日志；重启后进程会再次 `set_webhook`，请保持 `WEBHOOK_BASE_URL` 仍指向当前环境。

### 10.5 简要核对清单

- [ ] ZIP 内含 `main.py`、`requirements.txt` 与业务包目录。
- [ ] 已配置 `BOT_TOKEN`、`WEBHOOK_BASE_URL`（HTTPS 与 SLB 域名一致）。
- [ ] 入站：`POST` 能到达 `{WEBHOOK_BASE_URL}{WEBHOOK_PATH}`；出站可达 Telegram API。
- [ ] `bookmarks.db` 是否持久化。

### 10.6 使用阿里云 CLI 触发部署（可选）

将 ZIP 上传 OSS 后，若已安装 [阿里云 CLI](https://help.aliyun.com/zh/cli/)：

```bash
uv run python scripts/sae/deploy_sae.py \
  --region cn-hangzhou \
  --app-id <SAE应用ID> \
  --package-url <ZIP的OSS地址> \
  --package-version <版本号>
```

或使用环境变量 `SAE_REGION_ID`、`SAE_APP_ID`、`SAE_PACKAGE_URL`、`SAE_PACKAGE_VERSION`；加 `--dry-run` 仅打印命令。API：[DeployApplication](https://help.aliyun.com/zh/sae/api-sae-2019-05-06-deployapplication)（`PackageType=PythonZip`）。封装：`scripts/sae/deploy_sae.ps1`、`deploy_sae.sh`。

---

**版本说明**：以仓库内 `pyproject.toml`、`bot.py`（Webhook + aiohttp）、`config/settings.py` 及 `services/database.py` 为准；SAE 以当时控制台与 [ZIP 部署 Python 应用](https://help.aliyun.com/zh/sae/deploy-a-python-application-using-a-zip-package) 为准。
