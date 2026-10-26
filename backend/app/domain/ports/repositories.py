"""Portas de persistência local (cache de agendas, configuração e auditoria)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.entities import (
    Agenda,
    ConfiguracaoAgenda,
    ConfiguracaoTotem,
    LocalAtendimento,
    LogOperacao,
)


class AgendaRepository(Protocol):
    def substituir_todas(self, agendas: list[Agenda]) -> None: ...
    def listar(self, apenas_ativas: bool = True) -> list[Agenda]: ...
    def remover_inativas(self, exceto: set[str]) -> int:
        """Apaga do cadastro local as agendas inativas fora de `exceto`; devolve quantas."""
        ...


class LocalRepository(Protocol):
    def substituir_todos(self, locais: list[LocalAtendimento]) -> None: ...
    def listar(self) -> list[LocalAtendimento]: ...


class ConfiguracaoAgendaRepository(Protocol):
    def listar(self) -> list[ConfiguracaoAgenda]: ...
    def listar_monitoradas(self) -> list[ConfiguracaoAgenda]: ...
    def salvar_todas(self, configuracoes: list[ConfiguracaoAgenda]) -> None: ...


class ConfiguracaoTotemRepository(Protocol):
    """Linha única (singleton): modo do totem, agendas da recepção e agenda de encaixe."""

    def obter(self) -> ConfiguracaoTotem: ...
    def salvar(self, configuracao: ConfiguracaoTotem) -> None: ...


class LogOperacaoRepository(Protocol):
    def registrar(self, log: LogOperacao) -> LogOperacao: ...
    def listar_recentes(self, limite: int = 100) -> list[LogOperacao]: ...
    def apagar_anteriores_a(self, limite: datetime) -> int: ...


class SincronizacaoRepository(Protocol):
    def registrar_execucao(self, sucesso: bool, mensagem: str) -> None:
        """Guarda só a execução mais recente (é a única que o painel mostra)."""
        ...

    def ultima_execucao(self) -> dict | None: ...


class UnitOfWork(Protocol):
    """Agrupa repositórios em uma transação."""

    agendas: AgendaRepository
    locais: LocalRepository
    configuracoes: ConfiguracaoAgendaRepository
    totem: ConfiguracaoTotemRepository
    logs: LogOperacaoRepository
    sincronizacoes: SincronizacaoRepository

    def __enter__(self) -> UnitOfWork: ...
    def __exit__(self, *args) -> None: ...
    def commit(self) -> None: ...
