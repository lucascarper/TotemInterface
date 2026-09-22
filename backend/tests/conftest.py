from __future__ import annotations

from datetime import date, datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.api.container import build_container
from app.core.config import Settings
from app.domain.entities import ConfiguracaoAgenda, ConfiguracaoGuiches
from app.infrastructure.clock import TZ
from app.infrastructure.sgg.fake_gateway import SggFakeGateway
from app.main import create_app

HOJE = date(2026, 9, 17)


class FixedClock:
    def agora(self) -> datetime:
        return datetime.combine(HOJE, time(8, 15), TZ)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="sqlite://",
        sgg_mode="fake",
        admin_username="admin",
        admin_password="secret",
        jwt_secret="test-secret",
        totem_api_key="",
        _env_file=None,
    )


@pytest.fixture
def sgg() -> SggFakeGateway:
    return SggFakeGateway(hoje=HOJE)


@pytest.fixture
def container(settings, sgg):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    return build_container(settings, sgg=sgg, clock=FixedClock(), engine=engine)


@pytest.fixture
def container_configurado(container):
    """Sincroniza, monitora A1/A2 e configura os dois guichês (A4 e A6)."""
    container.sincronizar().executar()
    with container.uow as uow:
        uow.configuracoes.salvar_todas(
            [ConfiguracaoAgenda("A1", True), ConfiguracaoAgenda("A2", True)]
        )
        uow.guiches.salvar(ConfiguracaoGuiches("A4", "A6"))
        uow.commit()
    return container


@pytest.fixture
def client(settings, container_configurado):
    app = create_app(settings, container_configurado)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_headers(client):
    r = client.post("/admin/login", json={"username": "admin", "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
