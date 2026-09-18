from __future__ import annotations

from app.domain.entities import LogOperacao
from app.domain.ports import UnitOfWork


class ListarLogsUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def executar(self, limite: int = 100) -> list[LogOperacao]:
        with self._uow as uow:
            return uow.logs.listar_recentes(limite)
