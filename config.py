"""应用配置模块。

使用 pydantic-settings 从 .env 文件和环境变量加载配置。
模块级别实例化 Settings，导入时即校验 — bot_token 和 webhook_base_url 为必填项。
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram Bot ---
    bot_token: str
    webhook_base_url: str

    # --- Webhook ---
    webhook_path: str = "/webhook"
    webhook_secret: str | None = None
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080

    # --- 日志 ---
    log_level: str = "INFO"

    # --- 管理员 ---
    admin_ids: list[int] = []

    # --- PostgreSQL ---
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "pejortryia"
    db_password: str = ""
    db_name: str = "pejortryia"
    db_pool_min: int = 2
    db_pool_max: int = 10

    @property
    def database_url(self) -> str:
        """由各 DB_* 字段拼接 asyncpg 连接 DSN。"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @field_validator("webhook_base_url")
    @classmethod
    def _validate_webhook_base_url(cls, value: str) -> str:
        """强制 HTTPS 前缀，去除尾部斜杠以避免 URL 拼接时出现双斜杠。"""
        normalized = value.strip().rstrip("/")
        if not normalized.startswith("https://"):
            raise ValueError("WEBHOOK_BASE_URL must start with https://")
        return normalized

    @field_validator("webhook_path")
    @classmethod
    def _validate_webhook_path(cls, value: str) -> str:
        """确保路径以 '/' 开头，Telegram set_webhook 要求绝对路径。"""

        normalized = value.strip() or "/webhook"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized


settings = Settings()
