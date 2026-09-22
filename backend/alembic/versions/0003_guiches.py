"""guichês de atendimento (substitui encaixe por agenda monitorada)

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24

Também limpa, se existirem, os artefatos do encaixe automático periódico
(revertido no código): a coluna `incluir_da_unidade` e a tabela
`encaixes_automaticos`. Uso `IF EXISTS` de propósito — essa limpeza precisa
funcionar tanto num banco que nunca chegou a rodar aquela migração (veio
direto de "0001") quanto num que já rodou (veio de "0002" via a ponte em
0002_ponte_encaixe_automatico.py, cujo upgrade() não faz nada). Veja o
comentário naquele arquivo para o motivo de não fazer a limpeza lá.
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS encaixes_automaticos")
    op.execute("ALTER TABLE configuracoes_agenda DROP COLUMN IF EXISTS incluir_da_unidade")
    op.drop_column("configuracoes_agenda", "agenda_encaixe_id_sgg")
    op.drop_column("configuracoes_agenda", "encaixe_padrao")
    op.create_table(
        "configuracao_guiches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("guiche_1_agenda_id_sgg", sa.String(64)),
        sa.Column("guiche_2_agenda_id_sgg", sa.String(64)),
        sa.Column("ultimo_guiche_usado", sa.Integer),
    )


def downgrade() -> None:
    # Não recria os artefatos do encaixe automático: essa funcionalidade não
    # existe mais no código, só a coluna/tabela desta migração faz sentido
    # desfazer.
    op.drop_table("configuracao_guiches")
    op.add_column(
        "configuracoes_agenda",
        sa.Column("encaixe_padrao", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column("configuracoes_agenda", sa.Column("agenda_encaixe_id_sgg", sa.String(64)))
