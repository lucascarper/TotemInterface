"""Normalização de DATABASE_URL para plataformas tipo Railway/Heroku."""

import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (
            "postgres://user:pass@host:5432/db",
            "postgresql+psycopg://user:pass@host:5432/db",
        ),
        (
            "postgresql://user:pass@host:5432/db",
            "postgresql+psycopg://user:pass@host:5432/db",
        ),
        # Já com driver explícito: não mexe.
        (
            "postgresql+psycopg://user:pass@host:5432/db",
            "postgresql+psycopg://user:pass@host:5432/db",
        ),
        (
            "postgresql+psycopg2://user:pass@host:5432/db",
            "postgresql+psycopg2://user:pass@host:5432/db",
        ),
        # SQLite não é afetado.
        ("sqlite:///./totem.db", "sqlite:///./totem.db"),
        ("sqlite://", "sqlite://"),
    ],
)
def test_normaliza_database_url(entrada: str, esperado: str) -> None:
    s = Settings(_env_file=None, database_url=entrada)
    assert s.database_url == esperado
