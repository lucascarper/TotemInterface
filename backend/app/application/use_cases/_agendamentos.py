"""Regras compartilhadas sobre agendamentos do dia."""

from __future__ import annotations

from datetime import datetime

from app.domain.entities import Agendamento, StatusAgendamento
from app.domain.ports import SggGateway

STATUS_ELEGIVEIS_CHECKIN = {StatusAgendamento.AGENDADO}
STATUS_JA_EM_FILA = {StatusAgendamento.AGUARDANDO, StatusAgendamento.EM_ATENDIMENTO}


def listar_agendamentos_do_dia(
    sgg: SggGateway, paciente_id_sgg: str, agenda_ids: list[str], agora: datetime
) -> list[Agendamento]:
    if not agenda_ids:
        return []
    itens = sgg.listar_agendamentos(paciente_id_sgg, agenda_ids, agora.date())
    return sorted(itens, key=lambda a: a.data_hora)


def localizar_agendamento_do_dia(
    sgg: SggGateway, paciente_id_sgg: str, agenda_ids: list[str], agora: datetime
) -> Agendamento | None:
    """Primeiro agendamento do dia ainda pendente (AGENDADO) ou já em fila."""
    for a in listar_agendamentos_do_dia(sgg, paciente_id_sgg, agenda_ids, agora):
        if a.status in STATUS_ELEGIVEIS_CHECKIN | STATUS_JA_EM_FILA:
            return a
    return None
