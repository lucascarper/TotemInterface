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
                    incluir_da_unidade=c.incluir_da_unidade,
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
            chegada = {a.id_sgg for a in todas if a.por_ordem_chegada}
            self._validar(entradas, conhecidas, ativas, chegada)
            uow.configuracoes.salvar_todas(
                [
                    ConfiguracaoAgenda(
                        agenda_id_sgg=e.agenda_id_sgg,
                        monitorada=e.monitorada and e.agenda_id_sgg in ativas,
                        agenda_encaixe_id_sgg=(
                            e.agenda_encaixe_id_sgg
                            if e.monitorada and e.agenda_id_sgg in ativas
                            else None
                        ),
                        encaixe_padrao=(
                            e.encaixe_padrao and e.monitorada and e.agenda_id_sgg in ativas
                        ),
                        incluir_da_unidade=(
                            e.incluir_da_unidade
                            and e.monitorada
                            and e.agenda_id_sgg in ativas
                            and bool(e.agenda_encaixe_id_sgg)
                        ),
                    )
                    for e in entradas
                ]
            )
            uow.commit()

    @staticmethod
    def _validar(entradas, conhecidas: set[str], ativas: set[str], chegada: set[str]) -> None:
        ids = [e.agenda_id_sgg for e in entradas]
        if len(ids) != len(set(ids)):
            raise ConfiguracaoInvalidaError("Agenda repetida na configuração.")
        for e in entradas:
            if e.agenda_id_sgg not in conhecidas:
                raise ConfiguracaoInvalidaError(f"Agenda desconhecida: {e.agenda_id_sgg}")
            # Agenda inativa/excluída no SGG é sempre salva como desmarcada; só
            # validamos o encaixe das que continuam valendo.
            if not (e.monitorada and e.agenda_id_sgg in ativas):
                continue
            if e.incluir_da_unidade and not e.agenda_encaixe_id_sgg:
                raise ConfiguracaoInvalidaError(
                    "Para incluir agendamentos da unidade é preciso escolher a agenda de encaixe."
                )
            if not e.agenda_encaixe_id_sgg:
                continue
            if e.agenda_encaixe_id_sgg not in conhecidas:
                raise ConfiguracaoInvalidaError(
                    f"Agenda de encaixe desconhecida: {e.agenda_encaixe_id_sgg}"
                )
            if e.agenda_encaixe_id_sgg not in ativas:
                raise ConfiguracaoInvalidaError(
                    f"Encaixe {e.agenda_encaixe_id_sgg}: agenda inativa ou excluída no SGG."
                )
            if e.incluir_da_unidade and e.agenda_encaixe_id_sgg not in chegada:
                raise ConfiguracaoInvalidaError(
                    "A inclusão automática só funciona com agenda de encaixe por ordem de chegada."
                )
        padroes = [
            e for e in entradas if e.encaixe_padrao and e.monitorada and e.agenda_id_sgg in ativas
        ]
        if len(padroes) > 1:
            raise ConfiguracaoInvalidaError("Apenas uma agenda pode ser o encaixe padrão.")
        if padroes and not padroes[0].agenda_encaixe_id_sgg:
            raise ConfiguracaoInvalidaError("O encaixe padrão precisa ter agenda de encaixe.")
