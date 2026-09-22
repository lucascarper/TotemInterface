"""Gateway SGG em memória para desenvolvimento, demonstração e testes.

Simula pacientes, agendas e agendamentos com regras simples. Os CPFs abaixo são
válidos (dígitos verificadores corretos) e podem ser usados no totem em dev:

  529.982.247-25  Maria Aparecida da Silva  → tem agendamento hoje (AGENDADO)
  111.444.777-35  João Pedro Santos         → sem agendamento hoje (vai para encaixe)
  123.456.789-09  Ana Beatriz Oliveira      → já fez check-in hoje (AGUARDANDO)
  Qualquer outro CPF válido                 → paciente não cadastrado
"""

from __future__ import annotations

import itertools
import threading
from datetime import date, datetime, time

from app.domain.entities import (
    Agenda,
    Agendamento,
    Cpf,
    LocalAtendimento,
    Paciente,
    StatusAgendamento,
)
from app.domain.exceptions import SggOperacaoRecusadaError
from app.infrastructure.clock import TZ


class SggFakeGateway:
    def __init__(self, hoje: date | None = None) -> None:
        self._lock = threading.Lock()
        self._seq = itertools.count(1000)
        self._locais = [
            LocalAtendimento("L1", "Unidade Centro"),
            LocalAtendimento("L2", "Unidade Zona Norte"),
        ]
        self._agendas = [
            Agenda("A1", "Clínico Geral - Dr. Roberto", "L1", duracao_padrao_minutos=15),
            Agenda("A2", "Medicina do Trabalho - Dra. Carla", "L1", duracao_padrao_minutos=15),
            Agenda("A3", "Exames Ocupacionais", "L1", duracao_padrao_minutos=5),
            Agenda("A4", "Recepção", "L1", por_ordem_chegada=True),
            Agenda("A5", "Psicologia - Zona Norte", "L2", duracao_padrao_minutos=30),
            Agenda("A6", "Guichê 2", "L1", por_ordem_chegada=True),
        ]
        self._pacientes = {
            "52998224725": Paciente(
                "P1",
                "Maria Aparecida da Silva",
                Cpf("52998224725"),
                "1985-03-12",
                "11987654321",
                "E1",
            ),
            "11144477735": Paciente(
                "P2", "João Pedro Santos", Cpf("11144477735"), "1990-11-02", "11912345678", "E1"
            ),
            "12345678909": Paciente(
                "P3", "Ana Beatriz Oliveira", Cpf("12345678909"), "1978-07-25", None, "E2"
            ),
        }
        d = hoje or datetime.now(TZ).date()
        self._agendamentos: dict[str, Agendamento] = {
            "AG1": Agendamento(
                "AG1", "P1", "A1", datetime.combine(d, time(9, 30), TZ), StatusAgendamento.AGENDADO
            ),
            "AG2": Agendamento(
                "AG2",
                "P3",
                "A2",
                datetime.combine(d, time(10, 0), TZ),
                StatusAgendamento.AGUARDANDO,
            ),
        }

    # --- leitura -----------------------------------------------------------
    def listar_agendas(self) -> list[Agenda]:
        return [
            Agenda(
                a.id_sgg,
                a.nome,
                a.local_id_sgg,
                a.ativa,
                a.por_ordem_chegada,
                a.duracao_padrao_minutos,
            )
            for a in self._agendas
        ]

    def listar_locais(self) -> list[LocalAtendimento]:
        return list(self._locais)

    def buscar_paciente_por_cpf(self, cpf: Cpf) -> Paciente | None:
        return self._pacientes.get(cpf.digitos)

    def listar_agendamentos(self, paciente_id_sgg, agenda_ids_sgg, data) -> list[Agendamento]:
        return [
            a
            for a in self._agendamentos.values()
            if a.paciente_id_sgg == paciente_id_sgg
            and a.agenda_id_sgg in agenda_ids_sgg
            and a.data_hora.date() == data
        ]

    def listar_agendamentos_da_agenda(self, agenda_id_sgg, data) -> list[Agendamento]:
        return [
            a
            for a in self._agendamentos.values()
            if a.agenda_id_sgg == agenda_id_sgg and a.data_hora.date() == data
        ]

    # --- escrita -----------------------------------------------------------
    def atualizar_status_agendamento(self, agendamento_id_sgg, status) -> Agendamento:
        with self._lock:
            ag = self._agendamentos[agendamento_id_sgg]
            ag.status = status
            return ag

    def criar_agendamento(
        self, paciente, agenda_id_sgg, data_hora, tipo_atendimento, observacao=None
    ) -> Agendamento:
        novo_id = self._criar(paciente.id_sgg, agenda_id_sgg, data_hora)
        ag = self._agendamentos[novo_id]
        ag.tipo_atendimento, ag.observacao = tipo_atendimento, observacao
        return ag

    def _criar(self, funcionario_id, agenda_id_sgg, data_hora) -> str:
        with self._lock:
            agenda = next(a for a in self._agendas if a.id_sgg == agenda_id_sgg)
            if agenda.por_ordem_chegada and any(
                a.paciente_id_sgg == funcionario_id
                and a.agenda_id_sgg == agenda_id_sgg
                and a.data_hora.date() == data_hora.date()
                for a in self._agendamentos.values()
            ):
                # Regra real do SGG: uma por pessoa/dia em agenda por ordem de chegada,
                # mesmo que a anterior esteja cancelada.
                raise SggOperacaoRecusadaError(
                    "D16026", "O Funcionário já possui compromisso agendado nesta agenda."
                )
            novo_id = f"AG{next(self._seq)}"
            self._agendamentos[novo_id] = Agendamento(
                novo_id, funcionario_id, agenda_id_sgg, data_hora, StatusAgendamento.AGENDADO
            )
            return novo_id

    # --- utilidades para testes -------------------------------------------
    def adicionar_paciente(self, paciente: Paciente) -> None:
        self._pacientes[paciente.cpf.digitos] = paciente

    def adicionar_agendamento(self, ag: Agendamento) -> None:
        self._agendamentos[ag.id_sgg] = ag

    def obter_agendamento(self, id_sgg: str) -> Agendamento | None:
        return self._agendamentos.get(id_sgg)
