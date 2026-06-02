from functools import lru_cache
from typing import Any

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HealLink API"
    environment: str = "development"
    debug: bool = True
    auto_migrate: bool = True
    api_v1_prefix: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./heallink.db"  # raw value from .env

    @computed_field
    @property
    def database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql+psycopg://"):
            return url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if url.startswith("sqlite://"):
            return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    account_action_token_expire_hours: int = 24

    notifications_email_enabled: bool = False
    frontend_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_alternative_ports: list[int] = [2525, 587, 465]
    smtp_timeout_seconds: float = 30.0
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""

    chapa_base_url: str = "https://api.chapa.co"
    chapa_secret_key: str = ""
    chapa_public_key: str = ""
    chapa_callback_url: str = ""
    chapa_return_url: str = ""

    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("debug", "auto_migrate", mode="before")
    @classmethod
    def parse_boolish(cls, value: Any) -> Any:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "development", "dev", "true", "1", "yes", "on"}:
                return True
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
