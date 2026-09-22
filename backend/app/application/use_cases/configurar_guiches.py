"""Painel administrativo: os dois guichês de atendimento (global, não por agenda)."""

from __future__ import annotations

from app.application.dto import ConfiguracaoGuichesDTO
from app.domain.entities import ConfiguracaoGuiches
from app.domain.exceptions import ConfiguracaoInvalidaError
from app.domain.ports import UnitOfWork


class ObterGuichesUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def executar(self) -> ConfiguracaoGuichesDTO:
        with self._uow as uow:
            cfg = uow.guiches.obter()
            agendas = {a.id_sgg: a for a in uow.agendas.listar(apenas_ativas=False)}
        return ConfiguracaoGuichesDTO(
            guiche_1_agenda_id_sgg=cfg.guiche_1_agenda_id_sgg,
            guiche_1_agenda_nome=self._nome(agendas, cfg.guiche_1_agenda_id_sgg),
            guiche_2_agenda_id_sgg=cfg.guiche_2_agenda_id_sgg,
            guiche_2_agenda_nome=self._nome(agendas, cfg.guiche_2_agenda_id_sgg),
        )

    @staticmethod
    def _nome(agendas: dict, agenda_id: str | None) -> str | None:
        if not agenda_id or agenda_id not in agendas:
            return None
        return agendas[agenda_id].nome


class SalvarGuichesUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def executar(
        self, guiche_1_agenda_id_sgg: str | None, guiche_2_agenda_id_sgg: str | None
    ) -> None:
        with self._uow as uow:
            agendas = {a.id_sgg: a for a in uow.agendas.listar(apenas_ativas=False)}
            self._validar(guiche_1_agenda_id_sgg, guiche_2_agenda_id_sgg, agendas)
            atual = uow.guiches.obter()
            uow.guiches.salvar(
                ConfiguracaoGuiches(
                    guiche_1_agenda_id_sgg=guiche_1_agenda_id_sgg,
                    guiche_2_agenda_id_sgg=guiche_2_agenda_id_sgg,
                    ultimo_guiche_usado=atual.ultimo_guiche_usado,
                )
            )
            uow.commit()

    @staticmethod
    def _validar(g1: str | None, g2: str | None, agendas: dict) -> None:
        if g1 and g2 and g1 == g2:
            raise ConfiguracaoInvalidaError("Guichê 1 e Guichê 2 não podem ser a mesma agenda.")
        for agenda_id, rotulo in ((g1, "Guichê 1"), (g2, "Guichê 2")):
            if not agenda_id:
                continue
            agenda = agendas.get(agenda_id)
            if agenda is None:
                raise ConfiguracaoInvalidaError(f"{rotulo}: agenda desconhecida.")
            if not agenda.ativa:
                raise ConfiguracaoInvalidaError(f"{rotulo}: agenda inativa ou excluída no SGG.")
            if not agenda.por_ordem_chegada:
                raise ConfiguracaoInvalidaError(
                    f"{rotulo}: precisa ser uma agenda por ordem de chegada."
                )
