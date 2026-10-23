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

            ativas = {a.id_sgg for a in agendas if a.ativa}
            no_sgg = {a.id_sgg for a in agendas}
            limpas = 0

            # Agenda inativa ou excluída no SGG nunca é consultada: não deve ficar monitorada.
            existentes = {c.agenda_id_sgg: c for c in uow.configuracoes.listar()}
            configuracoes: list[ConfiguracaoAgenda] = []
            for a in agendas:
                cfg = existentes.get(a.id_sgg, ConfiguracaoAgenda(agenda_id_sgg=a.id_sgg))
                if not a.ativa and cfg.monitorada:
                    limpas += 1
                    cfg = ConfiguracaoAgenda(agenda_id_sgg=a.id_sgg)
                configuracoes.append(cfg)
            for id_sgg, cfg in existentes.items():
                if id_sgg not in no_sgg:
                    if cfg.monitorada:
                        limpas += 1
                    configuracoes.append(ConfiguracaoAgenda(agenda_id_sgg=id_sgg))
            uow.configuracoes.salvar_todas(configuracoes)

            # Recepção ou encaixe apontando para uma agenda excluída ou inativa: some sozinho,
            # para o check-in não continuar tentando escrever numa agenda que já não existe.
            totem = uow.totem.obter()
            recepcao = [a for a in totem.agendas_recepcao if a in ativas]
            encaixe = totem.agenda_encaixe_id_sgg if totem.agenda_encaixe_id_sgg in ativas else None
            if recepcao != totem.agendas_recepcao or encaixe != totem.agenda_encaixe_id_sgg:
                limpas += 1
                totem.agendas_recepcao = recepcao
                totem.agenda_encaixe_id_sgg = encaixe
                if totem.ultima_recepcao_usada not in recepcao:
                    totem.ultima_recepcao_usada = None
                uow.totem.salvar(totem)

            # Sucesso não vai para a auditoria: a cada poucos minutos, só esconderia os
            # eventos de paciente. Fica apenas a última execução, mostrada no painel.
            uow.sincronizacoes.registrar_execucao(
                True, f"{len(agendas)} agendas, {len(locais)} locais"
            )
            uow.commit()

        logger.info(
            "Sincronização: %d agendas, %d locais, %d configurações limpas",
            len(agendas),
            len(locais),
            limpas,
        )
        return ResultadoSincronizacaoDTO(len(agendas), len(locais), agora)
