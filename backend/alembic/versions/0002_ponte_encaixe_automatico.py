"""ponte: reverte o encaixe automático periódico (revertido no código)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24

Esta revisão existe só para dar continuidade ao histórico. Uma versão anterior
do código chegou a ser publicada com um "0002" que criava a coluna
`incluir_da_unidade` e a tabela `encaixes_automaticos` (funcionalidade de
encaixe automático periódico). Essa funcionalidade foi revertida no código
antes deste deploy, mas se aquele deploy já rodou em produção, o banco real
pode estar marcado na revisão "0002" — só que o arquivo antigo não existe
mais neste repositório.

Se eu simplesmente reaproveitasse o id "0002" com um `upgrade()` que desfaz
aquilo, o Alembic NÃO rodaria essa função num banco que já está marcado como
"0002" (ele só usa o id para achar o caminho até a revisão mais recente, não
para saber se o conteúdo mudou). Por isso este arquivo é um nó vazio no
histórico — não faz nada — e a limpeza de fato (`DROP ... IF EXISTS`) está em
`0003_guiches.py`, que sempre roda, venha o banco de "0001" ou de "0002".
"""

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
