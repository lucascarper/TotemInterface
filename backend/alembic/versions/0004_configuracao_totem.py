"""configuração do totem: modo, lista de agendas da recepção e agenda de encaixe

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-23

Substitui `configuracao_guiches` (exatamente dois guichês) por `configuracao_totem`, com uma
lista ordenada de agendas da recepção. Guichê 1 e Guichê 2 viram os dois primeiros itens.
"""

import sqlalchemy as sa

from alembic import op
from app.infrastructure.persistence.migracoes import migrar_guiches_para_totem

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuracao_totem",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("modo", sa.String(20), nullable=False),
        sa.Column("agendas_recepcao", sa.JSON, nullable=False),
        sa.Column("agenda_encaixe_id_sgg", sa.String(64)),
        sa.Column("ultima_recepcao_usada", sa.String(64)),
    )
    migrar_guiches_para_totem(op.get_bind())


def downgrade() -> None:
    op.create_table(
        "configuracao_guiches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("guiche_1_agenda_id_sgg", sa.String(64)),
        sa.Column("guiche_2_agenda_id_sgg", sa.String(64)),
        sa.Column("ultimo_guiche_usado", sa.Integer),
    )
    op.drop_table("configuracao_totem")
