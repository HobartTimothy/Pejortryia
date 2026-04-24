from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    webhook_base_url: str
    webhook_path: str = "/webhook"
    webhook_secret: str | None = None
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080
    log_level: str = "INFO"
    admin_ids: list[int] = []

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


settings = Settings()
