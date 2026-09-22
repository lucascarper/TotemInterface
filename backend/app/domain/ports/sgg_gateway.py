"""Porta de saída: tudo que o domínio precisa da API do SGG.

Qualquer adaptador (HTTP real, fake em memória, mock em testes) deve implementar
este protocolo. O domínio nunca conhece detalhes de transporte ou formato.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from app.domain.entities import (
    Agenda,
    Agendamento,
    Cpf,
    LocalAtendimento,
    Paciente,
    StatusAgendamento,
    TipoAtendimento,
)


class SggGateway(Protocol):
    def listar_agendas(self) -> list[Agenda]: ...

    def listar_locais(self) -> list[LocalAtendimento]: ...

    def buscar_paciente_por_cpf(self, cpf: Cpf) -> Paciente | None: ...

    def listar_agendamentos(
        self, paciente_id_sgg: str, agenda_ids_sgg: list[str], data: date
    ) -> list[Agendamento]: ...

    def listar_agendamentos_da_agenda(self, agenda_id_sgg: str, data: date) -> list[Agendamento]:
        """Todos os agendamentos do dia de uma agenda (qualquer pessoa) — usado para medir
        a carga de cada guichê (quantos estão Aguardando agora) ao distribuir check-ins."""
        ...

    def atualizar_status_agendamento(
        self, agendamento_id_sgg: str, status: StatusAgendamento
    ) -> Agendamento: ...

    def criar_agendamento(
        self,
        paciente: Paciente,
        agenda_id_sgg: str,
        data_hora: datetime,
        tipo_atendimento: TipoAtendimento,
        observacao: str | None = None,
    ) -> Agendamento: ...
