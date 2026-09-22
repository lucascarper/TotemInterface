"""schema inicial

Revision ID: 0001
Revises:
Create Date: 2026-09-17
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "locais_atendimento",
        sa.Column("id_sgg", sa.String(64), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("ativo", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "agendas",
        sa.Column("id_sgg", sa.String(64), primary_key=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("local_id_sgg", sa.String(64)),
        sa.Column("ativa", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("por_ordem_chegada", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("duracao_padrao_minutos", sa.Integer),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "configuracoes_agenda",
        sa.Column(
            "agenda_id_sgg",
            sa.String(64),
            sa.ForeignKey("agendas.id_sgg", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("monitorada", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("agenda_encaixe_id_sgg", sa.String(64)),
        sa.Column("encaixe_padrao", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "logs_operacao",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("sucesso", sa.Boolean, nullable=False),
        sa.Column("mensagem", sa.Text, nullable=False),
        sa.Column("cpf_mascarado", sa.String(20)),
        sa.Column("paciente_id_sgg", sa.String(64)),
        sa.Column("agendamento_id_sgg", sa.String(64)),
        sa.Column("agenda_id_sgg", sa.String(64)),
        sa.Column("tipo_atendimento", sa.String(20)),
        sa.Column("detalhes", sa.JSON),
    )
    op.create_index("ix_logs_operacao_criado_em", "logs_operacao", ["criado_em"])
    op.create_index("ix_logs_operacao_tipo", "logs_operacao", ["tipo"])
    op.create_table(
        "sincronizacoes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "executado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("sucesso", sa.Boolean, nullable=False),
        sa.Column("mensagem", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sincronizacoes")
    op.drop_index("ix_logs_operacao_tipo", table_name="logs_operacao")
    op.drop_index("ix_logs_operacao_criado_em", table_name="logs_operacao")
    op.drop_table("logs_operacao")
    op.drop_table("configuracoes_agenda")
    op.drop_table("agendas")
    op.drop_table("locais_atendimento")
