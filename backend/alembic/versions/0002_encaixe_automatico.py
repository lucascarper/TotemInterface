"""inclusão automática no encaixe

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-19
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "configuracoes_agenda",
        sa.Column("incluir_da_unidade", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "encaixes_automaticos",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("data", sa.Date, nullable=False),
        sa.Column("agenda_encaixe_id_sgg", sa.String(64), nullable=False),
        sa.Column("funcionario_id_sgg", sa.String(64), nullable=False),
        sa.Column("situacao", sa.String(20), nullable=False),
        sa.Column("agendamento_origem_id_sgg", sa.String(64)),
        sa.Column("agendamento_criado_id_sgg", sa.String(64)),
        sa.Column("detalhe", sa.Text),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "data", "agenda_encaixe_id_sgg", "funcionario_id_sgg", name="uq_encaixe_auto_dia_pessoa"
        ),
    )
    op.create_index("ix_encaixes_automaticos_data", "encaixes_automaticos", ["data"])


def downgrade() -> None:
    op.drop_index("ix_encaixes_automaticos_data", table_name="encaixes_automaticos")
    op.drop_table("encaixes_automaticos")
    op.drop_column("configuracoes_agenda", "incluir_da_unidade")
