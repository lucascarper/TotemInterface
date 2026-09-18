"""RF02/RF03 — painel administrativo: agendas monitoradas e agenda de encaixe."""

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
                    agenda_encaixe_id_sgg=c.agenda_encaixe_id_sgg,
                    encaixe_padrao=c.encaixe_padrao,
                )
            )
        return saida


class SalvarConfiguracoesUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def executar(self, entradas: list[ConfiguracaoAgendaEntradaDTO]) -> None:
        with self._uow as uow:
            conhecidas = {a.id_sgg for a in uow.agendas.listar(apenas_ativas=False)}
            self._validar(entradas, conhecidas)
            uow.configuracoes.salvar_todas(
                [
                    ConfiguracaoAgenda(
                        agenda_id_sgg=e.agenda_id_sgg,
                        monitorada=e.monitorada,
                        agenda_encaixe_id_sgg=e.agenda_encaixe_id_sgg if e.monitorada else None,
                        encaixe_padrao=e.encaixe_padrao and e.monitorada,
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
            if (
                e.monitorada
                and e.agenda_encaixe_id_sgg
                and e.agenda_encaixe_id_sgg not in conhecidas
            ):
                raise ConfiguracaoInvalidaError(
                    f"Agenda de encaixe desconhecida: {e.agenda_encaixe_id_sgg}"
                )
        padroes = [e for e in entradas if e.encaixe_padrao and e.monitorada]
        if len(padroes) > 1:
            raise ConfiguracaoInvalidaError("Apenas uma agenda pode ser o encaixe padrão.")
        if padroes and not padroes[0].agenda_encaixe_id_sgg:
            raise ConfiguracaoInvalidaError("O encaixe padrão precisa ter agenda de encaixe.")
