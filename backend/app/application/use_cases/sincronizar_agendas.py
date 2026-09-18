"""RF01 — sincroniza agendas e locais de atendimento do SGG para o cache local."""

from __future__ import annotations

import logging

from app.application.dto import ResultadoSincronizacaoDTO
from app.domain.entities import ConfiguracaoAgenda, LogOperacao, TipoOperacao
from app.domain.exceptions import SggIndisponivelError
from app.domain.ports import Clock, SggGateway, UnitOfWork

logger = logging.getLogger(__name__)


class SincronizarAgendasUseCase:
    def __init__(self, sgg: SggGateway, uow: UnitOfWork, clock: Clock) -> None:
        self._sgg = sgg
        self._uow = uow
        self._clock = clock

    def executar(self) -> ResultadoSincronizacaoDTO:
        agora = self._clock.agora()
        try:
            agendas = self._sgg.listar_agendas()
            locais = self._sgg.listar_locais()
        except SggIndisponivelError as exc:
            with self._uow as uow:
                uow.sincronizacoes.registrar_execucao(False, str(exc))
                uow.logs.registrar(LogOperacao(TipoOperacao.SINCRONIZACAO, False, f"Falha: {exc}"))
                uow.commit()
            raise

        with self._uow as uow:
            uow.agendas.substituir_todas(agendas)
            uow.locais.substituir_todos(locais)

            # Garante uma linha de configuração para cada agenda conhecida,
            # preservando o que o administrador já definiu.
            existentes = {c.agenda_id_sgg: c for c in uow.configuracoes.listar()}
            configuracoes = [
                existentes.get(a.id_sgg, ConfiguracaoAgenda(agenda_id_sgg=a.id_sgg))
                for a in agendas
            ]
            uow.configuracoes.salvar_todas(configuracoes)

            uow.sincronizacoes.registrar_execucao(
                True, f"{len(agendas)} agendas, {len(locais)} locais"
            )
            uow.logs.registrar(
                LogOperacao(
                    TipoOperacao.SINCRONIZACAO,
                    True,
                    "Sincronização concluída",
                    detalhes={"agendas": len(agendas), "locais": len(locais)},
                )
            )
            uow.commit()

        logger.info("Sincronização: %d agendas, %d locais", len(agendas), len(locais))
        return ResultadoSincronizacaoDTO(len(agendas), len(locais), agora)
