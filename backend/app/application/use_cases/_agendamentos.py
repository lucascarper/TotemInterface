"""Regras compartilhadas sobre agendamentos do dia."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
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
    ids = paciente.ids_vinculos
    data = agora.date()
    if len(ids) == 1:
        encontrados = [sgg.listar_agendamentos(ids[0], agenda_ids, data)]
    else:  # cada consulta é uma ida ao SGG: em paralelo, o custo é o da mais lenta
        with ThreadPoolExecutor(max_workers=min(len(ids), 4)) as pool:
            encontrados = list(
                pool.map(lambda i: sgg.listar_agendamentos(i, agenda_ids, data), ids)
            )
    itens = {a.id_sgg: a for lote in encontrados for a in lote}
    return sorted(itens.values(), key=lambda a: a.data_hora)


def paciente_do_agendamento(paciente: Paciente, agendamento: Agendamento | None) -> Paciente:
    """Funcionário e empresa em que o registro do guichê deve ser criado.

    Havendo agendamento no consultório, vale o dele (um CPF pode ter vínculos em várias
    empresas e o agendamento está preso a uma delas). Sem agendamento, o vínculo preferido.
    """
    if agendamento is None:
        return paciente
    empresa = agendamento.empresa_id_sgg or paciente.empresa_do_vinculo(agendamento.paciente_id_sgg)
    return replace(paciente, id_sgg=agendamento.paciente_id_sgg, empresa_id_sgg=empresa)


def empresa_ativa(sgg: SggGateway, alvo: Paciente) -> bool:
    """Empresa desconhecida conta como inativa: sem ela o SGG não aceita o registro."""
    return bool(alvo.empresa_id_sgg) and sgg.empresa_ativa(alvo.empresa_id_sgg)


def localizar_agendamento_do_dia(
    sgg: SggGateway, paciente: Paciente, agenda_ids: list[str], agora: datetime
) -> Agendamento | None:
    """Primeiro agendamento do dia ainda pendente (AGENDADO) ou já em fila."""
    for a in listar_agendamentos_do_dia(sgg, paciente, agenda_ids, agora):
        if a.status in STATUS_ELEGIVEIS_CHECKIN | STATUS_JA_EM_FILA:
            return a
    return None
