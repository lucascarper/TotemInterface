"""RF08/RF09 — realiza o check-in: sempre cria um registro num dos dois guichês.

Regras:
- Somente agendas marcadas como *monitoradas* (e os dois guichês) são consultadas.
- Se já existe um registro do dia em status AGUARDANDO/EM_ATENDIMENTO → check-in repetido
  (não duplica). Esse registro só vive num guichê: o totem nunca toca no agendamento
  original, então essa é a única fonte de verdade sobre "já chegou hoje".
- Havendo ou não um agendamento AGENDADO hoje, o resultado é sempre a criação de um novo
  registro, já em AGUARDANDO, num dos dois guichês. O agendamento original (se houver)
  nunca é alterado — fica intacto para referência/relatórios.
- Distribuição entre os guichês (motivo: o SGG só permite uma pessoa "Em Atendimento"
  por agenda, então um guichê travado numa consulta longa não pode travar o outro):
    1) Preferencial vai sempre para o Guichê 1.
    2) Normal vai para o guichê com menos gente "Aguardando" agora (consulta ao vivo no
       SGG); em caso de empate, alterna com quem foi usado por último (round-robin).
    3) Com um único guichê configurado, todo mundo vai para ele, sem distribuição.
- Toda operação é registrada para auditoria.
- Atendimento Preferencial ganha um marcador `[PREFERENCIAL]` no início da observação
  enviada ao SGG (veja `_observacao`), para se destacar em qualquer lista dentro do SGG.
"""

from __future__ import annotations

from datetime import date

from app.application.dto import CheckinDTO
from app.application.use_cases._agendamentos import (
    STATUS_ELEGIVEIS_CHECKIN,
    STATUS_JA_EM_FILA,
    agendas_consultadas,
    listar_agendamentos_do_dia,
)
from app.domain.entities import (
    Agendamento,
    ConfiguracaoGuiches,
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
                guiches = uow.guiches.obter()
                agendas = {a.id_sgg: a for a in uow.agendas.listar(apenas_ativas=False)}

            busca_ids = agendas_consultadas(configs, guiches)
            agendamentos = listar_agendamentos_do_dia(self._sgg, paciente.id_sgg, busca_ids, agora)

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

            destino, numero_guiche = self._resolver_guiche(guiches, tipo, agora.date())
            if destino is None:
                self._log(
                    TipoOperacao.CRIACAO_AGENDAMENTO,
                    False,
                    "Nenhum guichê configurado",
                    cpf,
                    tipo,
                    paciente_id=paciente.id_sgg,
                    agenda_id=pendente.agenda_id_sgg if pendente else None,
                )
                raise AgendaEncaixeNaoConfiguradaError()

            observacao = self._observacao(pendente, agendas, tipo)
            criado = self._sgg.criar_agendamento(
                paciente=paciente,
                agenda_id_sgg=destino,
                data_hora=agora,
                tipo_atendimento=tipo,
                observacao=observacao,
            )
            # O registro recém-criado já entra na fila de espera.
            try:
                criado = self._sgg.atualizar_status_agendamento(
                    criado.id_sgg, StatusAgendamento.AGUARDANDO
                )
            except SggIndisponivelError:
                # Registro existe; o status pode ser ajustado pela recepção.
                pass

            if numero_guiche is not None and tipo == TipoAtendimento.NORMAL:
                self._registrar_ultimo_guiche(numero_guiche)

            resultado = (
                ResultadoCheckin.AGENDAMENTO_CONFIRMADO
                if pendente
                else ResultadoCheckin.ENCAIXE_CRIADO
            )
            self._log(
                TipoOperacao.CRIACAO_AGENDAMENTO,
                True,
                "Agendamento confirmado na fila" if pendente else "Encaixe criado",
                cpf,
                tipo,
                paciente_id=paciente.id_sgg,
                agendamento_id=criado.id_sgg,
                agenda_id=destino,
            )

            # Ao paciente, mostramos o horário/agenda originais quando existirem — é a
            # informação que ele reconhece — mesmo que o registro criado esteja no guichê.
            if pendente:
                agenda_nome = self._nome_agenda(agendas, pendente.agenda_id_sgg)
                horario = pendente.data_hora
            else:
                agenda_nome = self._nome_agenda(agendas, destino)
                horario = criado.data_hora

            return CheckinDTO(
                resultado=resultado,
                paciente_nome=paciente.nome_publico,
                agendamento_id_sgg=criado.id_sgg,
                agenda_nome=agenda_nome,
                horario=horario,
                tipo_atendimento=tipo,
            )

        except SggIndisponivelError as exc:
            self._log(TipoOperacao.ERRO, False, f"SGG indisponível: {exc}", cpf, tipo)
            raise
        except SggOperacaoRecusadaError as exc:
            self._log(TipoOperacao.ERRO, False, f"SGG recusou: {exc}", cpf, tipo)
            raise

    def _resolver_guiche(
        self, guiches: ConfiguracaoGuiches, tipo: TipoAtendimento, hoje: date
    ) -> tuple[str | None, int | None]:
        """Devolve (agenda_id_sgg do destino, número do guichê) ou (None, None)."""
        g1, g2 = guiches.guiche_1_agenda_id_sgg, guiches.guiche_2_agenda_id_sgg
        if g1 and not g2:
            return g1, 1
        if g2 and not g1:
            return g2, 2
        if not g1 and not g2:
            return None, None

        # Os dois guichês existem: Preferencial sempre no 1; Normal por menor fila.
        if tipo == TipoAtendimento.PREFERENCIAL:
            return g1, 1

        carga_1 = self._carga_do_guiche(g1, hoje)
        carga_2 = self._carga_do_guiche(g2, hoje)
        if carga_1 < carga_2:
            return g1, 1
        if carga_2 < carga_1:
            return g2, 2
        # Empate: alterna com o último usado (round-robin), padrão para o 1.
        return (g2, 2) if guiches.ultimo_guiche_usado == 1 else (g1, 1)

    def _carga_do_guiche(self, agenda_id_sgg: str, hoje: date) -> int:
        itens = self._sgg.listar_agendamentos_da_agenda(agenda_id_sgg, hoje)
        return sum(1 for a in itens if a.status == StatusAgendamento.AGUARDANDO)

    def _registrar_ultimo_guiche(self, numero: int) -> None:
        with self._uow as uow:
            cfg = uow.guiches.obter()
            cfg.ultimo_guiche_usado = numero
            uow.guiches.salvar(cfg)
            uow.commit()

    def _observacao(
        self, pendente: Agendamento | None, agendas: dict, tipo: TipoAtendimento
    ) -> str:
        # Prefixo (não sufixo): listas do próprio SGG costumam truncar o texto pela
        # direita, então um "(preferencial)" no final pode nunca aparecer. Em caixa
        # alta e só ASCII para não depender de suporte a emoji/unicode na tela do SGG.
        prefixo = "[PREFERENCIAL] " if tipo == TipoAtendimento.PREFERENCIAL else ""
        if pendente is None:
            return f"{prefixo}Encaixe via totem"
        origem = self._nome_agenda(agendas, pendente.agenda_id_sgg)
        return f"{prefixo}Chegada via totem — agendado {pendente.data_hora:%H:%M} em {origem}"

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
