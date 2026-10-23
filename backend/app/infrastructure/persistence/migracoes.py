"""Migrações de dados usadas tanto pelo Alembic quanto pelo `AUTO_CREATE_SCHEMA`.

O paliativo na rede local cria o banco com `create_all` (sem Alembic). Sem isto, a troca
dos dois guichês pela lista de agendas da recepção apagaria a configuração em produção e
todo check-in falharia até alguém reconfigurar o painel.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.engine import Connection

_TOTEM = sa.table(
    "configuracao_totem",
    sa.column("id", sa.Integer),
    sa.column("modo", sa.String),
    sa.column("agendas_recepcao", sa.JSON),
    sa.column("agenda_encaixe_id_sgg", sa.String),
    sa.column("ultima_recepcao_usada", sa.String),
)


def migrar_guiches_para_totem(conn: Connection) -> None:
    """Copia Guichê 1 e Guichê 2 (nessa ordem) para `agendas_recepcao` e apaga a tabela antiga."""
    if not sa.inspect(conn).has_table("configuracao_guiches"):
        return
    ja_configurado = conn.execute(sa.text("SELECT COUNT(*) FROM configuracao_totem")).scalar()
    linha = conn.execute(
        sa.text(
            "SELECT guiche_1_agenda_id_sgg, guiche_2_agenda_id_sgg, ultimo_guiche_usado "
            "FROM configuracao_guiches WHERE id = 1"
        )
    ).first()
    if linha and not ja_configurado:
        g1, g2, ultimo = linha
        conn.execute(
            _TOTEM.insert().values(
                id=1,
                modo="CRIACAO",
                agendas_recepcao=[g for g in (g1, g2) if g],
                agenda_encaixe_id_sgg=None,
                ultima_recepcao_usada={1: g1, 2: g2}.get(ultimo),
            )
        )
    conn.execute(sa.text("DROP TABLE configuracao_guiches"))
