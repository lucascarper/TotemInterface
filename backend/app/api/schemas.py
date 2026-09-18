"""Contratos HTTP (Pydantic). Separados dos DTOs de aplicação de propósito."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities import ResultadoCheckin, TipoAtendimento, TipoOperacao


# ---- Totem ---------------------------------------------------------------
class IdentificarRequest(BaseModel):
    cpf: str = Field(..., min_length=11, max_length=14, examples=["529.982.247-25"])


class PacientePublico(BaseModel):
    id_sgg: str
    nome: str
    cpf_mascarado: str
    data_nascimento: str | None
    telefone_mascarado: str | None


class IdentificarResponse(BaseModel):
    paciente: PacientePublico
    possui_agendamento_hoje: bool
    agendamento_horario: datetime | None
    agenda_nome: str | None


class CheckinRequest(BaseModel):
    cpf: str = Field(..., min_length=11, max_length=14)
    tipo_atendimento: TipoAtendimento


class CheckinResponse(BaseModel):
    resultado: ResultadoCheckin
    paciente_nome: str
    agendamento_id_sgg: str
    agenda_nome: str
    horario: datetime
    tipo_atendimento: TipoAtendimento


class ErroResponse(BaseModel):
    codigo: str
    mensagem: str


# ---- Admin ---------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class ConfiguracaoAgendaItem(BaseModel):
    agenda_id_sgg: str
    agenda_nome: str
    local_nome: str | None
    ativa: bool
    por_ordem_chegada: bool
    monitorada: bool
    agenda_encaixe_id_sgg: str | None
    encaixe_padrao: bool


class ConfiguracaoAgendaEntrada(BaseModel):
    agenda_id_sgg: str
    monitorada: bool = False
    agenda_encaixe_id_sgg: str | None = None
    encaixe_padrao: bool = False


class SalvarConfiguracoesRequest(BaseModel):
    configuracoes: list[ConfiguracaoAgendaEntrada]


class SincronizacaoResponse(BaseModel):
    agendas: int
    locais: int
    executado_em: datetime


class StatusSincronizacao(BaseModel):
    executado_em: datetime | None
    sucesso: bool | None
    mensagem: str | None
    intervalo_segundos: int
    modo_sgg: str


class LogItem(BaseModel):
    id: int | None
    criado_em: datetime | None
    tipo: TipoOperacao
    sucesso: bool
    mensagem: str
    cpf_mascarado: str | None
    paciente_id_sgg: str | None
    agendamento_id_sgg: str | None
    agenda_id_sgg: str | None
    tipo_atendimento: TipoAtendimento | None
    detalhes: dict
