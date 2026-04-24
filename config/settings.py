from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从环境变量 / .env 文件读取并校验。

    字段无默认值时缺失即启动报错（如 bot_token），
    有默认值的字段可省略（如 log_level）。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略 .env 中多余的字段
    )

    bot_token: str  # Telegram Bot API Token，必填
    webhook_base_url: str  # Webhook HTTPS 前缀，必填（例如 https://bot.example.com）
    webhook_path: str = "/webhook"  # Webhook 路径
    webhook_secret: str | None = None  # 可选：Telegram Secret Token
    webhook_host: str = "0.0.0.0"  # 本地监听地址
    webhook_port: int = 8080  # 本地监听端口
    log_level: str = "INFO"  # 日志级别，默认 INFO
    admin_ids: list[int] = []  # 管理员用户 ID 列表，环境变量以逗号分隔

    @field_validator("webhook_base_url")
    @classmethod
    def _validate_webhook_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized.startswith("https://"):
            raise ValueError("WEBHOOK_BASE_URL must start with https://")
        return normalized

    @field_validator("webhook_path")
    @classmethod
    def _validate_webhook_path(cls, value: str) -> str:
        normalized = value.strip() or "/webhook"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized


settings = Settings()  # 模块级单例，导入时立即校验
