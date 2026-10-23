"""Entidades e objetos de valor do domínio de recepção.

Independentes de framework, banco ou API externa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.exceptions import CpfInvalidoError


class TipoAtendimento(StrEnum):
    PREFERENCIAL = "PREFERENCIAL"
    NORMAL = "NORMAL"


class StatusAgendamento(StrEnum):
    AGENDADO = "AGENDADO"
    AGUARDANDO = "AGUARDANDO"
    EM_ATENDIMENTO = "EM_ATENDIMENTO"
    ATENDIDO = "ATENDIDO"
    CANCELADO = "CANCELADO"
    FALTOU = "FALTOU"
    OUTRO = "OUTRO"


class ModoTotem(StrEnum):
    """Como o check-in registra a chegada no SGG."""

    CRIACAO = "CRIACAO"  # cria um registro novo numa agenda da recepção
    EDICAO = "EDICAO"  # muda o agendamento da recepção de Agendado para Aguardando


class TipoOperacao(StrEnum):
    BUSCA_PACIENTE = "BUSCA_PACIENTE"
    BUSCA_AGENDAMENTO = "BUSCA_AGENDAMENTO"
    ATUALIZACAO_STATUS = "ATUALIZACAO_STATUS"
    CRIACAO_AGENDAMENTO = "CRIACAO_AGENDAMENTO"
    SINCRONIZACAO = "SINCRONIZACAO"
    CONFIGURACAO = "CONFIGURACAO"
    ERRO = "ERRO"
    LEGADO = "LEGADO"
    """Tipo de log gravado por uma funcionalidade já removida do código (ex.: encaixe
    automático periódico). Mantido só para a auditoria conseguir exibir esses registros
    antigos sem quebrar; nenhum código novo deve gravar este valor."""


class ResultadoCheckin(StrEnum):
    """Resultado do check-in; só distingue a mensagem mostrada ao paciente."""

    AGENDAMENTO_CONFIRMADO = "AGENDAMENTO_CONFIRMADO"  # havia agendamento hoje
    ENCAIXE_CRIADO = "ENCAIXE_CRIADO"  # sem agendamento: entrou como encaixe


@dataclass(frozen=True, slots=True)
class Cpf:
    """Objeto de valor: CPF válido, sempre armazenado apenas com dígitos."""

    digitos: str

    def __post_init__(self) -> None:
        digitos = re.sub(r"\D", "", self.digitos or "")
        object.__setattr__(self, "digitos", digitos)
        if not self._valido(digitos):
            raise CpfInvalidoError("CPF inválido.")

    @staticmethod
    def _valido(d: str) -> bool:
        if len(d) != 11 or d == d[0] * 11:
            return False
        for tamanho in (9, 10):
            soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
            digito = (soma * 10) % 11
            if digito == 10:
                digito = 0
            if digito != int(d[tamanho]):
                return False
        return True

    @property
    def formatado(self) -> str:
        d = self.digitos
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"

    @property
    def mascarado(self) -> str:
        """Forma segura para logs e tela pública: ***.456.789-**"""
        d = self.digitos
        return f"***.{d[3:6]}.{d[6:9]}-**"


@dataclass(slots=True)
class LocalAtendimento:
    id_sgg: str
    nome: str
    ativo: bool = True


@dataclass(slots=True)
class Agenda:
    id_sgg: str
    nome: str
    local_id_sgg: str | None = None
    ativa: bool = True
    por_ordem_chegada: bool = False  # SGG: forma_atendimento "Chegada" (sem hora marcada)
    duracao_padrao_minutos: int | None = None


@dataclass(slots=True)
class Paciente:
    id_sgg: str
    nome: str
    cpf: Cpf
    data_nascimento: str | None = None  # ISO (YYYY-MM-DD)
    telefone: str | None = None
    empresa_id_sgg: str | None = None  # exigido pelo SGG ao criar agendamento
    # Todos os vínculos do CPF: id do funcionário -> id da empresa (um por empresa).
    vinculos: dict[str, str | None] = field(default_factory=dict)

    @property
    def ids_vinculos(self) -> tuple[str, ...]:
        return tuple(self.vinculos) or (self.id_sgg,)

    def empresa_do_vinculo(self, id_funcionario: str) -> str | None:
        if id_funcionario in self.vinculos:
            return self.vinculos[id_funcionario]
        return self.empresa_id_sgg if id_funcionario == self.id_sgg else None

    @property
    def nome_publico(self) -> str:
        """Nome reduzido para exibição em tela pública (primeiro e último nome)."""
        partes = self.nome.split()
        if len(partes) <= 2:
            return self.nome
        return f"{partes[0]} {partes[-1]}"

    @property
    def telefone_mascarado(self) -> str | None:
        if not self.telefone:
            return None
        d = re.sub(r"\D", "", self.telefone)
        return f"(**) *****-{d[-4:]}" if len(d) >= 4 else "****"


@dataclass(slots=True)
class Agendamento:
    id_sgg: str
    paciente_id_sgg: str
    agenda_id_sgg: str
    data_hora: datetime
    status: StatusAgendamento
    tipo_atendimento: TipoAtendimento | None = None
    observacao: str | None = None
    empresa_id_sgg: str | None = None


@dataclass(slots=True)
class ConfiguracaoAgenda:
    """Configuração administrativa de uma agenda do SGG dentro do totem."""

    agenda_id_sgg: str
    monitorada: bool = False


@dataclass(slots=True)
class ConfiguracaoTotem:
    """Configuração global do check-in (linha única).

    `agendas_recepcao` é ordenada e vale nos dois modos: no de criação é onde o registro de
    chegada nasce (o Preferencial vai para a primeira); no de edição é onde o agendamento do
    paciente é procurado. `agenda_encaixe_id_sgg` só é usada no modo de edição, para quem
    chega sem agendamento na recepção.
    """

    modo: ModoTotem = ModoTotem.CRIACAO
    agendas_recepcao: list[str] = field(default_factory=list)
    agenda_encaixe_id_sgg: str | None = None
    # Última agenda da recepção escolhida para um Normal no modo de criação, para alternar em
    # caso de empate na carga. Preferencial não altera isto.
    ultima_recepcao_usada: str | None = None


@dataclass(slots=True)
class LogOperacao:
    tipo: TipoOperacao
    sucesso: bool
    mensagem: str
    cpf_mascarado: str | None = None
    paciente_id_sgg: str | None = None
    agendamento_id_sgg: str | None = None
    agenda_id_sgg: str | None = None
    tipo_atendimento: TipoAtendimento | None = None
    detalhes: dict = field(default_factory=dict)
    criado_em: datetime | None = None
    id: int | None = None
