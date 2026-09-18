"""RF08/RF09 — realiza o check-in: atualiza status ou cria encaixe.

Regras:
- Somente agendas marcadas como *monitoradas* são consultadas.
- Se existe agendamento do dia com status AGENDADO → vira AGUARDANDO.
- Se já está AGUARDANDO/EM_ATENDIMENTO → check-in repetido (não duplica).
- Se não há agendamento → cria um novo na agenda de encaixe:
    1) a agenda de encaixe da configuração marcada como *padrão*;
    2) senão, a primeira agenda monitorada que tenha encaixe configurado.
- Toda operação é registrada para auditoria.
"""

from __future__ import annotations

from app.application.dto import CheckinDTO
from app.application.use_cases._agendamentos import (
    STATUS_ELEGIVEIS_CHECKIN,
    STATUS_JA_EM_FILA,
    listar_agendamentos_do_dia,
)
from app.domain.entities import (
    Cpf,
    LogOperacao,
    ResultadoCheckin,
    StatusAgendamento,
    TipoAtendimento,
    TipoOperacao,
)
from app.domain.exceptions import (
    AgendaEncaixeNaoConfiguradaError,
    CheckinJaRealizadoError,
    PacienteNaoEncontradoError,
    SggIndisponivelError,
    SggOperacaoRecusadaError,
)
from app.domain.ports import Clock, SggGateway, UnitOfWork


class RealizarCheckinUseCase:
    def __init__(self, sgg: SggGateway, uow: UnitOfWork, clock: Clock) -> None:
        self._sgg = sgg
        self._uow = uow
        self._clock = clock

    def executar(self, cpf_bruto: str, tipo: TipoAtendimento) -> CheckinDTO:
        cpf = Cpf(cpf_bruto)
        agora = self._clock.agora()

        try:
            paciente = self._sgg.buscar_paciente_por_cpf(cpf)
            if paciente is None:
                self._log(TipoOperacao.BUSCA_PACIENTE, False, "Paciente não cadastrado", cpf, tipo)
                raise PacienteNaoEncontradoError()

            with self._uow as uow:
                configs = uow.configuracoes.listar_monitoradas()
                agendas = {a.id_sgg: a for a in uow.agendas.listar(apenas_ativas=False)}

            monitoradas = [c.agenda_id_sgg for c in configs]
            agendamentos = listar_agendamentos_do_dia(
                self._sgg, paciente.id_sgg, monitoradas, agora
            )

            em_fila = next((a for a in agendamentos if a.status in STATUS_JA_EM_FILA), None)
            if em_fila:
                self._log(
                    TipoOperacao.ATUALIZACAO_STATUS,
                    False,
                    "Check-in já realizado",
                    cpf,
                    tipo,
                    paciente_id=paciente.id_sgg,
                    agendamento_id=em_fila.id_sgg,
                    agenda_id=em_fila.agenda_id_sgg,
                )
                raise CheckinJaRealizadoError()

            pendente = next((a for a in agendamentos if a.status in STATUS_ELEGIVEIS_CHECKIN), None)

            if pendente:
                atualizado = self._sgg.atualizar_status_agendamento(
                    pendente.id_sgg, StatusAgendamento.AGUARDANDO
                )
                self._log(
                    TipoOperacao.ATUALIZACAO_STATUS,
                    True,
                    "Agendado → Aguardando",
                    cpf,
                    tipo,
                    paciente_id=paciente.id_sgg,
                    agendamento_id=atualizado.id_sgg,
                    agenda_id=atualizado.agenda_id_sgg,
                )
                return CheckinDTO(
                    resultado=ResultadoCheckin.STATUS_ATUALIZADO,
                    paciente_nome=paciente.nome_publico,
                    agendamento_id_sgg=atualizado.id_sgg,
                    agenda_nome=self._nome_agenda(agendas, atualizado.agenda_id_sgg),
                    horario=atualizado.data_hora,
                    tipo_atendimento=tipo,
                )

            encaixe_id = self._resolver_agenda_encaixe(configs)
            if encaixe_id is None:
                self._log(
                    TipoOperacao.CRIACAO_AGENDAMENTO,
                    False,
                    "Sem agenda de encaixe configurada",
                    cpf,
                    tipo,
                    paciente_id=paciente.id_sgg,
                )
                raise AgendaEncaixeNaoConfiguradaError()

            criado = self._sgg.criar_agendamento(
                paciente=paciente,
                agenda_id_sgg=encaixe_id,
                data_hora=agora,
                tipo_atendimento=tipo,
                observacao=f"Encaixe via totem ({tipo.value.lower()})",
            )
            # O encaixe recém-criado já entra na fila de espera.
            try:
                criado = self._sgg.atualizar_status_agendamento(
                    criado.id_sgg, StatusAgendamento.AGUARDANDO
                )
            except SggIndisponivelError:
                # Encaixe existe; o status pode ser ajustado pela recepção.
                pass

            self._log(
                TipoOperacao.CRIACAO_AGENDAMENTO,
                True,
                "Encaixe criado",
                cpf,
                tipo,
                paciente_id=paciente.id_sgg,
                agendamento_id=criado.id_sgg,
                agenda_id=encaixe_id,
            )
            return CheckinDTO(
                resultado=ResultadoCheckin.ENCAIXE_CRIADO,
                paciente_nome=paciente.nome_publico,
                agendamento_id_sgg=criado.id_sgg,
                agenda_nome=self._nome_agenda(agendas, encaixe_id),
                horario=criado.data_hora,
                tipo_atendimento=tipo,
            )

        except SggIndisponivelError as exc:
            self._log(TipoOperacao.ERRO, False, f"SGG indisponível: {exc}", cpf, tipo)
            raise
        except SggOperacaoRecusadaError as exc:
            self._log(TipoOperacao.ERRO, False, f"SGG recusou: {exc}", cpf, tipo)
            raise

    @staticmethod
    def _resolver_agenda_encaixe(configs) -> str | None:
        padrao = next((c for c in configs if c.encaixe_padrao and c.agenda_encaixe_id_sgg), None)
        if padrao:
            return padrao.agenda_encaixe_id_sgg
        primeira = next((c for c in configs if c.agenda_encaixe_id_sgg), None)
        return primeira.agenda_encaixe_id_sgg if primeira else None

    @staticmethod
    def _nome_agenda(agendas, agenda_id: str) -> str:
        agenda = agendas.get(agenda_id)
        return agenda.nome if agenda else agenda_id

    def _log(
        self,
        tipo_op,
        sucesso,
        msg,
        cpf: Cpf,
        tipo_at,
        paciente_id=None,
        agendamento_id=None,
        agenda_id=None,
    ):
        with self._uow as uow:
            uow.logs.registrar(
                LogOperacao(
                    tipo=tipo_op,
                    sucesso=sucesso,
                    mensagem=msg,
                    cpf_mascarado=cpf.mascarado,
                    paciente_id_sgg=paciente_id,
                    agendamento_id_sgg=agendamento_id,
                    agenda_id_sgg=agenda_id,
                    tipo_atendimento=tipo_at,
                )
            )
            uow.commit()
