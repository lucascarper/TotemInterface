"""Os dois guichês viram a lista de agendas da recepção, com Alembic e sem ele."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.pool import StaticPool

from app.infrastructure.persistence.migracoes import migrar_guiches_para_totem
from app.infrastructure.persistence.models import Base

BACKEND = Path(__file__).resolve().parents[1]


def banco_com_guiches_antigos(g1, g2, ultimo):
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE configuracao_guiches (id INTEGER PRIMARY KEY, "
                "guiche_1_agenda_id_sgg VARCHAR(64), guiche_2_agenda_id_sgg VARCHAR(64), "
                "ultimo_guiche_usado INTEGER)"
            )
        )
        conn.execute(
            sa.text("INSERT INTO configuracao_guiches VALUES (1, :g1, :g2, :u)"),
            {"g1": g1, "g2": g2, "u": ultimo},
        )
    return engine


def totem(engine):
    with engine.connect() as conn:
        return conn.execute(
            sa.text(
                "SELECT modo, agendas_recepcao, agenda_encaixe_id_sgg, ultima_recepcao_usada "
                "FROM configuracao_totem"
            )
        ).first()


def test_guiches_viram_a_lista_da_recepcao_na_ordem():
    engine = banco_com_guiches_antigos("A4", "A6", 2)
    with engine.begin() as conn:
        migrar_guiches_para_totem(conn)
        migrar_guiches_para_totem(conn)  # rodar de novo não faz nada

    modo, recepcao, encaixe, ultima = totem(engine)
    assert modo == "CRIACAO" and recepcao == '["A4", "A6"]'
    assert encaixe is None and ultima == "A6"
    assert not sa.inspect(engine).has_table("configuracao_guiches")


def test_so_guiche_2_configurado():
    engine = banco_com_guiches_antigos(None, "A6", None)
    with engine.begin() as conn:
        migrar_guiches_para_totem(conn)
    assert totem(engine)[1] == '["A6"]'


def test_alembic_0004_a_partir_dos_guiches(tmp_path):
    """Aplica só a 0004 sobre um banco no estado da 0003 (a 0003 usa `DROP COLUMN IF EXISTS`,
    que só o PostgreSQL entende; a cadeia completa roda em produção, não em SQLite)."""
    banco = tmp_path / "totem.db"
    engine = sa.create_engine(f"sqlite:///{banco}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE configuracao_totem"))
        conn.execute(
            sa.text(
                "CREATE TABLE configuracao_guiches (id INTEGER PRIMARY KEY, "
                "guiche_1_agenda_id_sgg VARCHAR(64), guiche_2_agenda_id_sgg VARCHAR(64), "
                "ultimo_guiche_usado INTEGER)"
            )
        )
        conn.execute(sa.text("INSERT INTO configuracao_guiches VALUES (1, 'A4', 'A6', 1)"))
    engine.dispose()
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{banco}", "APP_ENV": "test"}

    def alembic(*args):
        r = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=BACKEND,
            env=env,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr[-2000:]

    alembic("stamp", "0003")
    alembic("upgrade", "head")

    with sqlite3.connect(banco) as conn:
        linha = conn.execute(
            "SELECT modo, agendas_recepcao, ultima_recepcao_usada FROM configuracao_totem"
        ).fetchone()
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert linha == ("CRIACAO", '["A4", "A6"]', "A4")
    assert "configuracao_guiches" not in tabelas

    alembic("downgrade", "0003")  # o caminho de volta também funciona
    with sqlite3.connect(banco) as conn:
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "configuracao_guiches" in tabelas and "configuracao_totem" not in tabelas


def test_paliativo_com_auto_create_schema_preserva_os_guiches(tmp_path, settings):
    """O paliativo sobe com AUTO_CREATE_SCHEMA sobre o SQLite existente, sem Alembic."""
    from app.api.container import build_container
    from app.infrastructure.sgg.fake_gateway import SggFakeGateway

    banco = tmp_path / "totem.db"
    engine = sa.create_engine(f"sqlite:///{banco}", connect_args={"check_same_thread": False})
    with engine.begin() as conn:  # banco criado pela versão anterior: só a tabela antiga
        conn.execute(
            sa.text(
                "CREATE TABLE configuracao_guiches (id INTEGER PRIMARY KEY, "
                "guiche_1_agenda_id_sgg VARCHAR(64), guiche_2_agenda_id_sgg VARCHAR(64), "
                "ultimo_guiche_usado INTEGER)"
            )
        )
        conn.execute(sa.text("INSERT INTO configuracao_guiches VALUES (1, 'A4', 'A6', NULL)"))

    container = build_container(settings, sgg=SggFakeGateway(), engine=engine)

    assert container.obter_totem().executar().modo == "CRIACAO"
    with container.uow as uow:
        assert uow.totem.obter().agendas_recepcao == ["A4", "A6"]
