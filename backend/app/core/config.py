"""Configuração centralizada via variáveis de ambiente (12-factor)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # Banco
    database_url: str = "sqlite:///./totem.db"
    auto_create_schema: bool = True

    @field_validator("database_url")
    @classmethod
    def _normalizar_database_url(cls, v: str) -> str:
        """Plataformas como Railway/Heroku injetam `postgres://` ou `postgresql://`
        sem driver explícito, o que faz o SQLAlchemy tentar usar psycopg2 (não
        instalado neste projeto — usamos psycopg 3). Reescrevemos para o driver
        correto sem exigir que a variável de ambiente seja editada manualmente."""
        for prefixo in ("postgres://", "postgresql://"):
            if v.startswith(prefixo) and not v.startswith("postgresql+"):
                return "postgresql+psycopg://" + v[len(prefixo) :]
        return v

    # SGG
    sgg_mode: Literal["fake", "http"] = "fake"
    sgg_base_url: str = "https://app.sgg.net.br/api/v3/"
    sgg_api_key: str = ""
    sgg_timeout_seconds: float = 8.0
    sync_interval_seconds: int = 300

    # Inclusão automática no encaixe (só age nas agendas com a opção ligada no painel).
    encaixe_auto_interval_seconds: int = 300
    # Limite de escritas por execução: a API do SGG aceita 60 requisições/min.
    encaixe_auto_max_por_execucao: int = 20

    # Admin / auth
    admin_username: str = "admin"
    admin_password: str = "admin123"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expires_minutes: int = 480

    # Totem
    totem_api_key: str = ""

    # Lista separada por vírgula (mantida como texto para não ser interpretada como JSON).
    cors_origins: str = "http://localhost:5173"
    # Em desenvolvimento, aceita qualquer porta de localhost (previews, tablets via túnel local).
    cors_origin_regex: str | None = None

    @property
    def cors_origin_regex_efetivo(self) -> str | None:
        if self.cors_origin_regex:
            return self.cors_origin_regex
        if self.app_env == "development":
            return r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
        return None

    @property
    def cors_origins_list(self) -> list[str]:
        return [v.strip() for v in self.cors_origins.split(",") if v.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
