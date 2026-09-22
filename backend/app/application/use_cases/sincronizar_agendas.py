"""RF01 — sincroniza agendas e locais de atendimento do SGG para o cache local."""

from __future__ import annotations

import logging

from app.application.dto import ResultadoSincronizacaoDTO
from app.domain.entities import ConfiguracaoAgenda, ConfiguracaoGuiches, LogOperacao, TipoOperacao
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

            # Guichê apontando para uma agenda excluída ou inativa: some sozinho, para o
            # check-in não continuar tentando escrever numa agenda que já não existe mais.
            guiches = uow.guiches.obter()
            g1 = guiches.guiche_1_agenda_id_sgg
            g2 = guiches.guiche_2_agenda_id_sgg
            novo_g1 = g1 if g1 in ativas else None
            novo_g2 = g2 if g2 in ativas else None
            if novo_g1 != g1 or novo_g2 != g2:
                limpas += 1
                uow.guiches.salvar(
                    ConfiguracaoGuiches(novo_g1, novo_g2, guiches.ultimo_guiche_usado)
                )

            uow.sincronizacoes.registrar_execucao(
                True, f"{len(agendas)} agendas, {len(locais)} locais"
            )
            uow.logs.registrar(
                LogOperacao(
                    TipoOperacao.SINCRONIZACAO,
                    True,
                    "Sincronização concluída",
                    detalhes={
                        "agendas": len(agendas),
                        "locais": len(locais),
                        "configuracoes_limpas": limpas,
                    },
                )
            )
            uow.commit()

        logger.info("Sincronização: %d agendas, %d locais", len(agendas), len(locais))
        return ResultadoSincronizacaoDTO(len(agendas), len(locais), agora)
