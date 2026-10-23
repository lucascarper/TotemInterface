"""Painel administrativo: modo do totem, agendas da recepção e agenda de encaixe."""

from __future__ import annotations

from app.application.dto import AgendaResumoDTO, ConfiguracaoTotemDTO
from app.domain.entities import Agenda, ConfiguracaoTotem, LogOperacao, ModoTotem, TipoOperacao
from app.domain.exceptions import ConfiguracaoInvalidaError
from app.domain.ports import UnitOfWork

ROTULO_MODO = {
    ModoTotem.CRIACAO: "criação (cria registro na recepção)",
    ModoTotem.EDICAO: "edição (marca o agendamento como Aguardando)",
}


def _resumo(agendas: dict[str, Agenda], agenda_id: str) -> AgendaResumoDTO:
    agenda = agendas.get(agenda_id)
    if agenda is None:
        return AgendaResumoDTO(agenda_id, agenda_id, ativa=False, por_ordem_chegada=False)
    return AgendaResumoDTO(agenda.id_sgg, agenda.nome, agenda.ativa, agenda.por_ordem_chegada)


class ObterConfiguracaoTotemUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def executar(self) -> ConfiguracaoTotemDTO:
        with self._uow as uow:
            cfg = uow.totem.obter()
            agendas = {a.id_sgg: a for a in uow.agendas.listar(apenas_ativas=False)}
        encaixe = cfg.agenda_encaixe_id_sgg
        return ConfiguracaoTotemDTO(
            modo=cfg.modo,
            agendas_recepcao=[_resumo(agendas, a) for a in cfg.agendas_recepcao],
            agenda_encaixe=_resumo(agendas, encaixe) if encaixe else None,
        )


class SalvarConfiguracaoTotemUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def executar(
        self,
        modo: ModoTotem,
        agendas_recepcao: list[str],
        agenda_encaixe_id_sgg: str | None,
        usuario: str,
    ) -> None:
        with self._uow as uow:
            agendas = {a.id_sgg: a for a in uow.agendas.listar(apenas_ativas=False)}
            self._validar(modo, agendas_recepcao, agenda_encaixe_id_sgg, agendas)
            atual = uow.totem.obter()
            ultima = atual.ultima_recepcao_usada
            uow.totem.salvar(
                ConfiguracaoTotem(
                    modo=modo,
                    agendas_recepcao=list(agendas_recepcao),
                    agenda_encaixe_id_sgg=agenda_encaixe_id_sgg,
                    ultima_recepcao_usada=ultima if ultima in agendas_recepcao else None,
                )
            )
            if modo != atual.modo:
                uow.logs.registrar(
                    LogOperacao(
                        TipoOperacao.CONFIGURACAO,
                        True,
                        f"Modo do totem alterado para {ROTULO_MODO[modo]} por {usuario}",
                    )
                )
            uow.commit()

    @staticmethod
    def _validar(
        modo: ModoTotem,
        recepcao: list[str],
        encaixe: str | None,
        agendas: dict[str, Agenda],
    ) -> None:
        if len(set(recepcao)) != len(recepcao):
            raise ConfiguracaoInvalidaError("A mesma agenda aparece duas vezes na recepção.")
        for agenda_id in recepcao:
            agenda = agendas.get(agenda_id)
            if agenda is None:
                raise ConfiguracaoInvalidaError(f"Recepção: agenda desconhecida ({agenda_id}).")
            if not agenda.ativa:
                raise ConfiguracaoInvalidaError(
                    f"Recepção: {agenda.nome} está inativa ou excluída no SGG."
                )
        if encaixe:
            agenda = agendas.get(encaixe)
            if agenda is None:
                raise ConfiguracaoInvalidaError("Encaixe: agenda desconhecida.")
            if not agenda.ativa:
                raise ConfiguracaoInvalidaError("Encaixe: agenda inativa ou excluída no SGG.")
            if not agenda.por_ordem_chegada:
                raise ConfiguracaoInvalidaError(
                    "Encaixe: precisa ser uma agenda por ordem de chegada."
                )
            if encaixe in recepcao:
                raise ConfiguracaoInvalidaError(
                    "Encaixe: não pode ser uma das agendas da recepção."
                )
        if modo == ModoTotem.EDICAO:
            if not recepcao:
                raise ConfiguracaoInvalidaError(
                    "Modo de edição: escolha ao menos uma agenda da recepção."
                )
            if not encaixe:
                raise ConfiguracaoInvalidaError(
                    "Modo de edição: escolha a agenda de encaixe, para quem chega sem agendamento."
                )
