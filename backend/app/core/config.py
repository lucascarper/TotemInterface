"""Configuração centralizada via variáveis de ambiente (12-factor)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # Banco
    database_url: str = "sqlite:///./totem.db"
    auto_create_schema: bool = True

    # SGG
    sgg_mode: Literal["fake", "http"] = "fake"
    sgg_base_url: str = "https://app.sgg.net.br/api/v3/"
    sgg_api_key: str = ""
    sgg_timeout_seconds: float = 8.0
    sync_interval_seconds: int = 300

    # Admin / auth
    admin_username: str = "admin"
    admin_password: str = "admin123"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expires_minutes: int = 480

    # Totem
    totem_api_key: str = ""

    # Lista separada por vírgula (mantida como texto para não ser interpretada como JSON).
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [v.strip() for v in self.cors_origins.split(",") if v.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
