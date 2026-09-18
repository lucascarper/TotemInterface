"""DTOs de entrada/saída dos casos de uso (sem dependência de FastAPI)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.entities import ResultadoCheckin, TipoAtendimento


@dataclass(frozen=True, slots=True)
class PacientePublicoDTO:
    """Apenas os dados mínimos para o paciente confirmar em tela pública."""

    id_sgg: str
    nome: str
    cpf_mascarado: str
    data_nascimento: str | None
    telefone_mascarado: str | None


@dataclass(frozen=True, slots=True)
class IdentificacaoDTO:
    paciente: PacientePublicoDTO
    possui_agendamento_hoje: bool
    agendamento_horario: datetime | None
    agenda_nome: str | None


@dataclass(frozen=True, slots=True)
class CheckinDTO:
    resultado: ResultadoCheckin
    paciente_nome: str
    agendamento_id_sgg: str
    agenda_nome: str
    horario: datetime
    tipo_atendimento: TipoAtendimento


@dataclass(frozen=True, slots=True)
class ConfiguracaoAgendaEntradaDTO:
    agenda_id_sgg: str
    monitorada: bool
    agenda_encaixe_id_sgg: str | None
    encaixe_padrao: bool = False


@dataclass(frozen=True, slots=True)
class ConfiguracaoAgendaSaidaDTO:
    agenda_id_sgg: str
    agenda_nome: str
    local_nome: str | None
    ativa: bool
    por_ordem_chegada: bool
    monitorada: bool
    agenda_encaixe_id_sgg: str | None
    encaixe_padrao: bool


@dataclass(frozen=True, slots=True)
class ResultadoSincronizacaoDTO:
    agendas: int
    locais: int
    executado_em: datetime
    detalhes: dict = field(default_factory=dict)
