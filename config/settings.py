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

    bot_token: str          # Telegram Bot API Token，必填
    log_level: str = "INFO"  # 日志级别，默认 INFO
    admin_ids: list[int] = []  # 管理员用户 ID 列表，环境变量以逗号分隔


settings = Settings()  # 模块级单例，导入时立即校验
