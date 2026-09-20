from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.persistence.repositories import (
    SqlAgendaRepository,
    SqlConfiguracaoAgendaRepository,
    SqlEncaixeAutomaticoRepository,
    SqlLocalRepository,
    SqlLogOperacaoRepository,
    SqlSincronizacaoRepository,
)


class SqlAlchemyUnitOfWork:
    """Uma transação por bloco `with`. Reentrante: cada `with` abre nova sessão."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._factory()
        s = self._session
        self.agendas = SqlAgendaRepository(s)
        self.locais = SqlLocalRepository(s)
        self.configuracoes = SqlConfiguracaoAgendaRepository(s)
        self.logs = SqlLogOperacaoRepository(s)
        self.sincronizacoes = SqlSincronizacaoRepository(s)
        self.encaixes_automaticos = SqlEncaixeAutomaticoRepository(s)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self._session is not None
        try:
            if exc_type is not None:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None

    def commit(self) -> None:
        assert self._session is not None
        self._session.commit()

    def rollback(self) -> None:
        assert self._session is not None
        self._session.rollback()
