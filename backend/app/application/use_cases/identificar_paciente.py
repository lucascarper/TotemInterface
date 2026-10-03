"""RF05/RF06/RF07/RF10 — localiza o paciente pelo CPF e prepara dados para confirmação."""

from __future__ import annotations

from app.application.dto import IdentificacaoDTO, PacientePublicoDTO
from app.application.use_cases._agendamentos import (
    STATUS_ELEGIVEIS_CHECKIN,
    agendas_consultadas,
    empresa_ativa,
    localizar_agendamento_do_dia,
    paciente_do_agendamento,
)
from app.domain.entities import Cpf, LogOperacao, TipoOperacao
from app.domain.exceptions import (
    EmpresaInativaError,
    PacienteNaoEncontradoError,
    SggIndisponivelError,
)
from app.domain.ports import Clock, SggGateway, UnitOfWork


class IdentificarPacienteUseCase:
    def __init__(self, sgg: SggGateway, uow: UnitOfWork, clock: Clock) -> None:
        self._sgg = sgg
        self._uow = uow
        self._clock = clock

    def executar(self, cpf_bruto: str) -> IdentificacaoDTO:
        cpf = Cpf(cpf_bruto)  # levanta CpfInvalidoError

        try:
            paciente = self._sgg.buscar_paciente_por_cpf(cpf)
        except SggIndisponivelError as exc:
            self._log(TipoOperacao.ERRO, False, f"SGG indisponível na busca: {exc}", cpf)
            raise

        if paciente is None:
            self._log(TipoOperacao.BUSCA_PACIENTE, False, "Paciente não cadastrado", cpf)
            raise PacienteNaoEncontradoError()

        with self._uow as uow:
            configs = uow.configuracoes.listar_monitoradas()
            guiches = uow.guiches.obter()
            monitoradas = agendas_consultadas(configs, guiches)
            agendas = {a.id_sgg: a for a in uow.agendas.listar(apenas_ativas=False)}

        agendamento = localizar_agendamento_do_dia(
            self._sgg, paciente, monitoradas, self._clock.agora()
        )

        # Avisa já aqui (e não depois de o paciente confirmar) quando o check-in seria recusado
        # por empresa inativa. Registro já na fila segue para o aviso de "chegada já registrada".
        if agendamento is None or agendamento.status in STATUS_ELEGIVEIS_CHECKIN:
            alvo = paciente_do_agendamento(paciente, agendamento)
            if not empresa_ativa(self._sgg, alvo):
                self._log(
                    TipoOperacao.BUSCA_PACIENTE,
                    False,
                    "Empresa inativa",
                    cpf,
                    paciente_id=alvo.id_sgg,
                    agendamento_id=agendamento.id_sgg if agendamento else None,
                )
                raise EmpresaInativaError()

        self._log(
            TipoOperacao.BUSCA_PACIENTE,
            True,
            "Paciente localizado",
            cpf,
            paciente_id=paciente.id_sgg,
            agendamento_id=agendamento.id_sgg if agendamento else None,
        )

        agenda_nome = (
            agendas[agendamento.agenda_id_sgg].nome
            if agendamento and agendamento.agenda_id_sgg in agendas
            else None
        )
        return IdentificacaoDTO(
            paciente=PacientePublicoDTO(
                id_sgg=paciente.id_sgg,
                nome=paciente.nome_publico,
                cpf_mascarado=cpf.mascarado,
                data_nascimento=paciente.data_nascimento,
                telefone_mascarado=paciente.telefone_mascarado,
            ),
            possui_agendamento_hoje=agendamento is not None,
            agendamento_horario=agendamento.data_hora if agendamento else None,
            agenda_nome=agenda_nome,
        )

    def _log(self, tipo, sucesso, msg, cpf: Cpf, paciente_id=None, agendamento_id=None):
        with self._uow as uow:
            uow.logs.registrar(
                LogOperacao(
                    tipo=tipo,
                    sucesso=sucesso,
                    mensagem=msg,
                    cpf_mascarado=cpf.mascarado,
                    paciente_id_sgg=paciente_id,
                    agendamento_id_sgg=agendamento_id,
                )
            )
            uow.commit()
