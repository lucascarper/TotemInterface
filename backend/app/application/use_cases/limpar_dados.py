"""Limpeza periódica do banco local.

O totem só arbitra o que acontece no SGG (que guarda o histórico oficial dos agendamentos);
aqui fica apenas a configuração e uma auditoria recente para investigar reclamações.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, timedelta

from app.domain.ports import Clock, UnitOfWork

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResultadoLimpezaDTO:
    logs_apagados: int
    agendas_apagadas: int
    compactado: bool


class LimparDadosUseCase:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        retencao_logs_dias: int,
        compactar_banco: Callable[[], bool] | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._retencao = retencao_logs_dias
        self._compactar_banco = compactar_banco

    def executar(self, compactar: bool = False) -> ResultadoLimpezaDTO:
        # Datas no banco estão em UTC (SQLite guarda sem fuso).
        limite = self._clock.agora().astimezone(UTC) - timedelta(days=self._retencao)
        with self._uow as uow:
            logs = uow.logs.apagar_anteriores_a(limite)
            totem = uow.totem.obter()
            em_uso = {c.agenda_id_sgg for c in uow.configuracoes.listar() if c.monitorada}
            em_uso |= set(totem.agendas_recepcao)
            if totem.agenda_encaixe_id_sgg:
                em_uso.add(totem.agenda_encaixe_id_sgg)
            agendas = uow.agendas.remover_inativas(exceto=em_uso)
            uow.commit()

        compactado = bool(compactar and self._compactar_banco and self._compactar_banco())
        logger.info(
            "Limpeza: %d registros de auditoria e %d agendas inativas apagados%s",
            logs,
            agendas,
            "; banco compactado" if compactado else "",
        )
        return ResultadoLimpezaDTO(logs, agendas, compactado)
