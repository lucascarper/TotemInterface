"""Regras compartilhadas sobre agendamentos do dia."""

from __future__ import annotations

from datetime import datetime

from app.domain.entities import Agendamento, Paciente, StatusAgendamento
from app.domain.ports import SggGateway

STATUS_ELEGIVEIS_CHECKIN = {StatusAgendamento.AGENDADO}
STATUS_JA_EM_FILA = {StatusAgendamento.AGUARDANDO, StatusAgendamento.EM_ATENDIMENTO}


def agendas_consultadas(configs, guiches) -> list[str]:
    """Monitoradas + os dois guichês de atendimento.

    O check-in sempre cria (ou encontra) o registro de chegada num guichê, então
    os dois precisam entrar na busca: senão um segundo check-in no mesmo dia
    tentaria criar outro registro lá, e o SGG recusaria (D16026).
    """
    ids = [c.agenda_id_sgg for c in configs]
    ids += [g for g in (guiches.guiche_1_agenda_id_sgg, guiches.guiche_2_agenda_id_sgg) if g]
    return list(dict.fromkeys(ids))


def listar_agendamentos_do_dia(
    sgg: SggGateway, paciente: Paciente, agenda_ids: list[str], agora: datetime
) -> list[Agendamento]:
    """Agendamentos do dia em qualquer vínculo (empresa) do CPF.

    O agendamento fica preso ao funcionário da empresa em que foi marcado, que nem sempre é
    o vínculo que o gateway considera o preferido; por isso busca em todos.
    """
    if not agenda_ids:
        return []
    itens: dict[str, Agendamento] = {}
    for id_funcionario in paciente.ids_vinculos:
        for a in sgg.listar_agendamentos(id_funcionario, agenda_ids, agora.date()):
            itens[a.id_sgg] = a
    return sorted(itens.values(), key=lambda a: a.data_hora)


def localizar_agendamento_do_dia(
    sgg: SggGateway, paciente: Paciente, agenda_ids: list[str], agora: datetime
) -> Agendamento | None:
    """Primeiro agendamento do dia ainda pendente (AGENDADO) ou já em fila."""
    for a in listar_agendamentos_do_dia(sgg, paciente, agenda_ids, agora):
        if a.status in STATUS_ELEGIVEIS_CHECKIN | STATUS_JA_EM_FILA:
            return a
    return None
