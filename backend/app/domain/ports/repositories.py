"""Portas de persistência local (cache de agendas, configuração e auditoria)."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from app.domain.entities import Agenda, ConfiguracaoAgenda, LocalAtendimento, LogOperacao


class AgendaRepository(Protocol):
    def substituir_todas(self, agendas: list[Agenda]) -> None: ...
    def listar(self, apenas_ativas: bool = True) -> list[Agenda]: ...
    def obter(self, agenda_id_sgg: str) -> Agenda | None: ...


class LocalRepository(Protocol):
    def substituir_todos(self, locais: list[LocalAtendimento]) -> None: ...
    def listar(self) -> list[LocalAtendimento]: ...


class ConfiguracaoAgendaRepository(Protocol):
    def listar(self) -> list[ConfiguracaoAgenda]: ...
    def listar_monitoradas(self) -> list[ConfiguracaoAgenda]: ...
    def salvar_todas(self, configuracoes: list[ConfiguracaoAgenda]) -> None: ...


class LogOperacaoRepository(Protocol):
    def registrar(self, log: LogOperacao) -> LogOperacao: ...
    def listar_recentes(self, limite: int = 100) -> list[LogOperacao]: ...


class SincronizacaoRepository(Protocol):
    def registrar_execucao(self, sucesso: bool, mensagem: str) -> None: ...
    def ultima_execucao(self) -> dict | None: ...


class EncaixeAutomaticoRepository(Protocol):
    """Livro-razão das inclusões automáticas: garante uma por pessoa/agenda/dia."""

    def situacoes_do_dia(self, data: date, agenda_encaixe_id_sgg: str) -> dict[str, str]: ...

    def registrar(
        self,
        data: date,
        agenda_encaixe_id_sgg: str,
        funcionario_id_sgg: str,
        situacao: str,
        agendamento_origem_id_sgg: str | None = None,
        agendamento_criado_id_sgg: str | None = None,
        detalhe: str | None = None,
    ) -> bool: ...


class UnitOfWork(Protocol):
    """Agrupa repositórios em uma transação."""

    agendas: AgendaRepository
    locais: LocalRepository
    configuracoes: ConfiguracaoAgendaRepository
    logs: LogOperacaoRepository
    sincronizacoes: SincronizacaoRepository
    encaixes_automaticos: EncaixeAutomaticoRepository

    def __enter__(self) -> UnitOfWork: ...
    def __exit__(self, *args) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
