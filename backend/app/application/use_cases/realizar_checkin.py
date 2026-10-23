"""RF08/RF09 — realiza o check-in, em um de dois modos configurados no painel.

Modo de criação (padrão):
- Consulta as agendas *monitoradas* e as agendas da recepção.
- Se já existe um registro de chegada do dia que ainda não foi atendido (AGUARDANDO, EM_ATENDIMENTO
  ou outro status na recepção diferente de ATENDIDO e AGENDADO) → check-in repetido, não duplica.
- Havendo ou não agendamento AGENDADO hoje, sempre cria um novo registro, já em AGUARDANDO, numa
  agenda da recepção. O agendamento original nunca é alterado.
- Paciente já atendido pode voltar: o novo registro vai para uma agenda da recepção onde ele ainda
  não tem registro hoje (o SGG recusa dois do mesmo paciente na mesma agenda de ordem de chegada
  no mesmo dia, D16026). Sem nenhuma disponível, recusa com ENCAIXE_NAO_CONFIGURADO.
- Distribuição (o SGG só permite uma pessoa "Em Atendimento" por agenda):
    1) Preferencial vai para a primeira agenda da recepção disponível.
    2) Normal vai para a de menos gente "Aguardando" agora; no empate, alterna a partir da última
       usada (round-robin pela ordem da lista).
- O registro usa o funcionário e a empresa do agendamento encontrado (sem agendamento, o vínculo
  preferido do CPF). Preferencial ganha `[PREFERENCIAL]` no início da observação.

Modo de edição:
- Consulta só as agendas da recepção (e a de encaixe, para saber se ele já passou por lá hoje).
- O primeiro agendamento AGENDADO do dia na recepção vira AGUARDANDO; nada é criado. A API só
  altera situação, então o Preferencial fica registrado apenas na auditoria.
- Sem agendamento AGENDADO (inclusive Faltou, Cancelado ou já atendido que voltou): cria o
  encaixe na agenda de encaixe, já em AGUARDANDO. Só cabe um por dia nessa agenda (D16026); quem
  já tem registro lá hoje é orientado a procurar a recepção.

Nos dois modos: empresa inativa recusa com EMPRESA_INATIVA antes de qualquer escrita, e toda
operação é registrada para auditoria.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

from app.application.dto import CheckinDTO
from app.application.use_cases._agendamentos import (
    STATUS_ELEGIVEIS_CHECKIN,
    STATUS_JA_EM_FILA,
    agendas_consultadas,
    bloqueia_nova_chegada,
    empresa_ativa,
    listar_agendamentos_do_dia,
    paciente_do_agendamento,
)
from app.domain.entities import (
    Agendamento,
    ConfiguracaoTotem,
    Cpf,
    LogOperacao,
    ModoTotem,
    Paciente,
    ResultadoCheckin,
    StatusAgendamento,
    TipoAtendimento,
    TipoOperacao,
)
from app.domain.exceptions import (
    AgendaEncaixeNaoConfiguradaError,
    CheckinJaRealizadoError,
    EmpresaInativaError,
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
                totem = uow.totem.obter()
                agendas = {a.id_sgg: a for a in uow.agendas.listar(apenas_ativas=False)}

            if totem.modo == ModoTotem.EDICAO:
                return self._por_edicao(cpf, tipo, agora, paciente, totem, agendas)
            return self._por_criacao(cpf, tipo, agora, paciente, configs, totem, agendas)

        except SggIndisponivelError as exc:
            self._log(TipoOperacao.ERRO, False, f"SGG indisponível: {exc}", cpf, tipo)
            raise
        except SggOperacaoRecusadaError as exc:
            self._log(TipoOperacao.ERRO, False, f"SGG recusou: {exc}", cpf, tipo)
            raise

    # ------------------------------------------------------------------ criação
    def _por_criacao(
        self,
        cpf: Cpf,
        tipo: TipoAtendimento,
        agora: datetime,
        paciente: Paciente,
        configs,
        totem: ConfiguracaoTotem,
        agendas: dict,
    ) -> CheckinDTO:
        recepcao_ids = set(totem.agendas_recepcao)
        agendamentos = listar_agendamentos_do_dia(
            self._sgg, paciente, agendas_consultadas(configs, totem), agora
        )

        em_fila = next((a for a in agendamentos if bloqueia_nova_chegada(a, recepcao_ids)), None)
        if em_fila:
            self._recusar_ja_registrado(cpf, tipo, em_fila)

        # Agendamento marcado na recepção não é "o agendamento" do paciente neste modo: o que
        # conta é o dos consultórios (monitoradas).
        pendente = next(
            (
                a
                for a in agendamentos
                if a.status in STATUS_ELEGIVEIS_CHECKIN and a.agenda_id_sgg not in recepcao_ids
            ),
            None,
        )

        # O registro da recepção nasce no mesmo funcionário/empresa do agendamento encontrado.
        alvo = paciente_do_agendamento(paciente, pendente)
        self._exigir_empresa_ativa(cpf, tipo, alvo, pendente.agenda_id_sgg if pendente else None)

        ocupadas = {a.agenda_id_sgg for a in agendamentos if a.agenda_id_sgg in recepcao_ids}
        destino = self._resolver_recepcao(totem, tipo, agora.date(), excluir=ocupadas)
        if destino is None:
            motivo = (
                "Paciente já tem registro em todas as agendas da recepção hoje"
                if recepcao_ids
                else "Nenhuma agenda da recepção configurada"
            )
            self._log(
                TipoOperacao.CRIACAO_AGENDAMENTO,
                False,
                motivo,
                cpf,
                tipo,
                paciente_id=alvo.id_sgg,
                agenda_id=pendente.agenda_id_sgg if pendente else None,
            )
            raise AgendaEncaixeNaoConfiguradaError()

        criado = self._criar_aguardando(alvo, destino, agora, tipo, pendente, agendas)
        if tipo == TipoAtendimento.NORMAL:
            self._registrar_ultima_recepcao(destino)

        self._log(
            TipoOperacao.CRIACAO_AGENDAMENTO,
            True,
            "Agendamento confirmado na fila" if pendente else "Encaixe criado",
            cpf,
            tipo,
            paciente_id=alvo.id_sgg,
            agendamento_id=criado.id_sgg,
            agenda_id=destino,
        )

        # Ao paciente, mostramos o horário/agenda originais quando existirem: é a informação
        # que ele reconhece, mesmo que o registro criado esteja na recepção.
        if pendente:
            return self._dto(
                ResultadoCheckin.AGENDAMENTO_CONFIRMADO, paciente, criado, agendas, pendente, tipo
            )
        return self._dto(ResultadoCheckin.ENCAIXE_CRIADO, paciente, criado, agendas, criado, tipo)

    def _resolver_recepcao(
        self,
        totem: ConfiguracaoTotem,
        tipo: TipoAtendimento,
        hoje: date,
        excluir: set[str] = frozenset(),
    ) -> str | None:
        """Agenda da recepção que recebe o registro, ou None se não houver nenhuma disponível.

        `excluir` são agendas em que o paciente já tem registro hoje (o SGG não aceita outro).
        """
        disponiveis = [a for a in totem.agendas_recepcao if a not in excluir]
        if not disponiveis:
            return None
        if len(disponiveis) == 1 or tipo == TipoAtendimento.PREFERENCIAL:
            return disponiveis[0]

        with ThreadPoolExecutor(max_workers=min(len(disponiveis), 4)) as pool:
            cargas = dict(
                zip(disponiveis, pool.map(lambda a: self._carga(a, hoje), disponiveis), strict=True)
            )
        menor = min(cargas.values())
        empatadas = [a for a in disponiveis if cargas[a] == menor]
        if len(empatadas) == 1 or totem.ultima_recepcao_usada not in totem.agendas_recepcao:
            return empatadas[0]
        # Empate: a próxima da lista depois da última usada (dá a volta no fim).
        ordem = totem.agendas_recepcao
        i = ordem.index(totem.ultima_recepcao_usada)
        return next(a for a in ordem[i + 1 :] + ordem[: i + 1] if a in empatadas)

    def _carga(self, agenda_id_sgg: str, hoje: date) -> int:
        itens = self._sgg.listar_agendamentos_da_agenda(agenda_id_sgg, hoje)
        return sum(1 for a in itens if a.status == StatusAgendamento.AGUARDANDO)

    def _registrar_ultima_recepcao(self, agenda_id_sgg: str) -> None:
        with self._uow as uow:
            cfg = uow.totem.obter()
            cfg.ultima_recepcao_usada = agenda_id_sgg
            uow.totem.salvar(cfg)
            uow.commit()

    # ------------------------------------------------------------------ edição
    def _por_edicao(
        self,
        cpf: Cpf,
        tipo: TipoAtendimento,
        agora: datetime,
        paciente: Paciente,
        totem: ConfiguracaoTotem,
        agendas: dict,
    ) -> CheckinDTO:
        recepcao_ids = set(totem.agendas_recepcao)
        encaixe = totem.agenda_encaixe_id_sgg
        busca = list(dict.fromkeys(totem.agendas_recepcao + ([encaixe] if encaixe else [])))
        agendamentos = listar_agendamentos_do_dia(self._sgg, paciente, busca, agora)

        em_fila = next(
            (
                a
                for a in agendamentos
                if (a.agenda_id_sgg in recepcao_ids and a.status in STATUS_JA_EM_FILA)
                or (
                    a.agenda_id_sgg == encaixe
                    and a.status in STATUS_JA_EM_FILA | {StatusAgendamento.AGENDADO}
                )
            ),
            None,
        )
        if em_fila:
            self._recusar_ja_registrado(cpf, tipo, em_fila)

        pendente = next(
            (
                a
                for a in agendamentos
                if a.agenda_id_sgg in recepcao_ids and a.status in STATUS_ELEGIVEIS_CHECKIN
            ),
            None,
        )
        if pendente:
            return self._marcar_aguardando(cpf, tipo, paciente, pendente, agendas)
        return self._criar_encaixe(cpf, tipo, agora, paciente, encaixe, agendamentos, agendas)

    def _marcar_aguardando(
        self,
        cpf: Cpf,
        tipo: TipoAtendimento,
        paciente: Paciente,
        pendente: Agendamento,
        agendas: dict,
    ) -> CheckinDTO:
        alvo = paciente_do_agendamento(paciente, pendente)
        self._exigir_empresa_ativa(cpf, tipo, alvo, pendente.agenda_id_sgg)
        atualizado = self._sgg.atualizar_status_agendamento(
            pendente.id_sgg, StatusAgendamento.AGUARDANDO
        )
        self._log(
            TipoOperacao.ATUALIZACAO_STATUS,
            True,
            "Agendamento marcado como Aguardando",
            cpf,
            tipo,
            paciente_id=alvo.id_sgg,
            agendamento_id=pendente.id_sgg,
            agenda_id=pendente.agenda_id_sgg,
        )
        return self._dto(
            ResultadoCheckin.AGENDAMENTO_CONFIRMADO, paciente, atualizado, agendas, pendente, tipo
        )

    def _criar_encaixe(
        self,
        cpf: Cpf,
        tipo: TipoAtendimento,
        agora: datetime,
        paciente: Paciente,
        encaixe: str | None,
        agendamentos: list[Agendamento],
        agendas: dict,
    ) -> CheckinDTO:
        motivo = None
        if not encaixe:
            motivo = "Agenda de encaixe não configurada"
        elif any(a.agenda_id_sgg == encaixe for a in agendamentos):
            # O SGG só aceita um registro por paciente por dia nessa agenda (D16026).
            motivo = "Paciente já passou pela agenda de encaixe hoje"
        if motivo:
            self._log(
                TipoOperacao.CRIACAO_AGENDAMENTO,
                False,
                motivo,
                cpf,
                tipo,
                paciente_id=paciente.id_sgg,
                agenda_id=encaixe,
            )
            raise AgendaEncaixeNaoConfiguradaError()

        self._exigir_empresa_ativa(cpf, tipo, paciente, encaixe)
        criado = self._criar_aguardando(paciente, encaixe, agora, tipo, None, agendas)
        self._log(
            TipoOperacao.CRIACAO_AGENDAMENTO,
            True,
            "Encaixe criado",
            cpf,
            tipo,
            paciente_id=paciente.id_sgg,
            agendamento_id=criado.id_sgg,
            agenda_id=encaixe,
        )
        return self._dto(ResultadoCheckin.ENCAIXE_CRIADO, paciente, criado, agendas, criado, tipo)

    # ------------------------------------------------------------------ comum
    def _recusar_ja_registrado(self, cpf: Cpf, tipo: TipoAtendimento, registro: Agendamento):
        self._log(
            TipoOperacao.ATUALIZACAO_STATUS,
            False,
            "Check-in já realizado",
            cpf,
            tipo,
            paciente_id=registro.paciente_id_sgg,
            agendamento_id=registro.id_sgg,
            agenda_id=registro.agenda_id_sgg,
        )
        raise CheckinJaRealizadoError()

    def _exigir_empresa_ativa(
        self, cpf: Cpf, tipo: TipoAtendimento, alvo: Paciente, agenda_id: str | None
    ) -> None:
        if empresa_ativa(self._sgg, alvo):
            return
        self._log(
            TipoOperacao.CRIACAO_AGENDAMENTO,
            False,
            "Empresa inativa",
            cpf,
            tipo,
            paciente_id=alvo.id_sgg,
            agenda_id=agenda_id,
        )
        raise EmpresaInativaError()

    def _criar_aguardando(
        self,
        alvo: Paciente,
        agenda_id_sgg: str,
        agora: datetime,
        tipo: TipoAtendimento,
        pendente: Agendamento | None,
        agendas: dict,
    ) -> Agendamento:
        criado = self._sgg.criar_agendamento(
            paciente=alvo,
            agenda_id_sgg=agenda_id_sgg,
            data_hora=agora,
            tipo_atendimento=tipo,
            observacao=self._observacao(pendente, agendas, tipo, agora),
        )
        # O registro recém-criado já entra na fila de espera.
        try:
            return self._sgg.atualizar_status_agendamento(
                criado.id_sgg, StatusAgendamento.AGUARDANDO
            )
        except SggIndisponivelError:
            return criado  # o registro existe; a recepção ajusta o status, se preciso

    def _dto(
        self,
        resultado: ResultadoCheckin,
        paciente: Paciente,
        registro: Agendamento,
        agendas: dict,
        exibido: Agendamento,
        tipo: TipoAtendimento,
    ) -> CheckinDTO:
        return CheckinDTO(
            resultado=resultado,
            paciente_nome=paciente.nome_publico,
            agendamento_id_sgg=registro.id_sgg,
            agenda_nome=self._nome_agenda(agendas, exibido.agenda_id_sgg),
            horario=exibido.data_hora,
            tipo_atendimento=tipo,
        )

    def _observacao(
        self,
        pendente: Agendamento | None,
        agendas: dict,
        tipo: TipoAtendimento,
        agora: datetime,
    ) -> str:
        # Prefixo (não sufixo): listas do próprio SGG costumam truncar o texto pela
        # direita, então um "(preferencial)" no final pode nunca aparecer. Em caixa
        # alta e só ASCII para não depender de suporte a emoji/unicode na tela do SGG.
        # Pelo mesmo motivo, o separador é um hífen simples, não um em-dash unicode
        # (que aparecia como "?" na tela do SGG).
        prefixo = "[PREFERENCIAL] " if tipo == TipoAtendimento.PREFERENCIAL else ""
        hora_chegada = f"{agora:%H:%M}"
        if pendente is None:
            return f"{prefixo}Encaixe via totem {hora_chegada}"
        origem = self._nome_agenda(agendas, pendente.agenda_id_sgg)
        return (
            f"{prefixo}Chegada via totem {hora_chegada} - agendado "
            f"{pendente.data_hora:%H:%M} em {origem}"
        )

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
