"""RF02 — painel administrativo: quais agendas do SGG o totem monitora."""

from __future__ import annotations

from app.application.dto import ConfiguracaoAgendaEntradaDTO, ConfiguracaoAgendaSaidaDTO
from app.domain.entities import ConfiguracaoAgenda
from app.domain.exceptions import ConfiguracaoInvalidaError
from app.domain.ports import UnitOfWork


class ListarConfiguracoesUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def executar(self) -> list[ConfiguracaoAgendaSaidaDTO]:
        with self._uow as uow:
            agendas = uow.agendas.listar(apenas_ativas=False)
            locais = {loc.id_sgg: loc.nome for loc in uow.locais.listar()}
            configs = {c.agenda_id_sgg: c for c in uow.configuracoes.listar()}

        saida = []
        for a in sorted(agendas, key=lambda x: x.nome.lower()):
            c = configs.get(a.id_sgg, ConfiguracaoAgenda(agenda_id_sgg=a.id_sgg))
            saida.append(
                ConfiguracaoAgendaSaidaDTO(
                    agenda_id_sgg=a.id_sgg,
                    agenda_nome=a.nome,
                    local_nome=locais.get(a.local_id_sgg) if a.local_id_sgg else None,
                    ativa=a.ativa,
                    por_ordem_chegada=a.por_ordem_chegada,
                    monitorada=c.monitorada,
                )
            )
        return saida


class SalvarConfiguracoesUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def executar(self, entradas: list[ConfiguracaoAgendaEntradaDTO]) -> None:
        with self._uow as uow:
            todas = uow.agendas.listar(apenas_ativas=False)
            conhecidas = {a.id_sgg for a in todas}
            ativas = {a.id_sgg for a in todas if a.ativa}
            self._validar(entradas, conhecidas)
            uow.configuracoes.salvar_todas(
                [
                    ConfiguracaoAgenda(
                        agenda_id_sgg=e.agenda_id_sgg,
                        monitorada=e.monitorada and e.agenda_id_sgg in ativas,
                    )
                    for e in entradas
                ]
            )
            uow.commit()

    @staticmethod
    def _validar(entradas, conhecidas: set[str]) -> None:
        ids = [e.agenda_id_sgg for e in entradas]
        if len(ids) != len(set(ids)):
            raise ConfiguracaoInvalidaError("Agenda repetida na configuração.")
        for e in entradas:
            if e.agenda_id_sgg not in conhecidas:
                raise ConfiguracaoInvalidaError(f"Agenda desconhecida: {e.agenda_id_sgg}")
