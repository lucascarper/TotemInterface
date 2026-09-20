"""Inclusão automática, na agenda de encaixe, dos agendamentos das outras agendas da unidade.

Para cada agenda monitorada com a opção ligada, olha os agendamentos **de hoje** das
demais agendas da mesma unidade de atendimento e inclui a pessoa na agenda de encaixe
configurada, para que ela entre na fila de chegada e possa fazer check-in no totem.

Regras:
- Só agendamentos com status Agendado contam (cancelado, faltou, atendido e aguardando não).
- Fontes: agendas ativas da unidade que **não** são monitoradas nem de encaixe (as
  monitoradas já são atendidas diretamente pelo totem).
- Uma única inclusão por pessoa, por agenda de encaixe e por dia, mesmo que a pessoa tenha
  vários agendamentos nas outras agendas. Não inclui quem já tem qualquer agendamento (de
  qualquer status) na agenda de encaixe naquele dia, pois o SGG também recusa (D16026).
- Só funciona com agenda de encaixe por ordem de chegada (sem horário a escolher).
- `simular=True` não escreve nada: informa o que seria incluído.
"""

from __future__ import annotations

import logging
import time

from app.application.dto import InclusaoDTO, ResultadoEncaixeAutomaticoDTO
from app.domain.entities import (
    Agenda,
    Agendamento,
    LogOperacao,
    StatusAgendamento,
    TipoOperacao,
)
from app.domain.exceptions import SggIndisponivelError, SggOperacaoRecusadaError
from app.domain.ports import Clock, SggGateway, UnitOfWork

logger = logging.getLogger(__name__)

# Código do SGG: o funcionário já tem agendamento nessa agenda por ordem de chegada no dia.
JA_POSSUI_AGENDAMENTO = "D16026"


class IncluirNoEncaixeUseCase:
    def __init__(
        self,
        sgg: SggGateway,
        uow: UnitOfWork,
        clock: Clock,
        max_por_execucao: int = 20,
        pausa_entre_escritas: float = 1.0,
    ) -> None:
        self._sgg = sgg
        self._uow = uow
        self._clock = clock
        self._max = max_por_execucao
        self._pausa = pausa_entre_escritas

    def executar(self, simular: bool = False) -> ResultadoEncaixeAutomaticoDTO:
        agora = self._clock.agora()
        hoje = agora.date()
        avisos: list[str] = []

        with self._uow as uow:
            configs = uow.configuracoes.listar_monitoradas()
            agendas = {a.id_sgg: a for a in uow.agendas.listar(apenas_ativas=False)}

        monitoradas = {c.agenda_id_sgg for c in configs}
        encaixes = {c.agenda_encaixe_id_sgg for c in configs if c.agenda_encaixe_id_sgg}

        # encaixe -> unidades cujas agendas alimentam esse encaixe
        unidades_por_encaixe: dict[str, set[str]] = {}
        for c in configs:
            if not c.agenda_encaixe_id_sgg or not (simular or c.incluir_da_unidade):
                continue
            origem = agendas.get(c.agenda_id_sgg)
            encaixe = agendas.get(c.agenda_encaixe_id_sgg)
            nome = origem.nome if origem else c.agenda_id_sgg
            if origem is None or not origem.local_id_sgg:
                avisos.append(f"{nome}: agenda sem unidade de atendimento; ignorada.")
            elif encaixe is None or not encaixe.ativa:
                avisos.append(f"{nome}: agenda de encaixe inativa ou inexistente; ignorada.")
            elif not encaixe.por_ordem_chegada:
                avisos.append(
                    f"{nome}: a agenda de encaixe '{encaixe.nome}' não é por ordem de "
                    "chegada; ignorada."
                )
            else:
                unidades_por_encaixe.setdefault(encaixe.id_sgg, set()).add(origem.local_id_sgg)

        resultado = _Acumulador(simulado=simular, avisos=avisos)
        criados = 0

        for encaixe_id, unidades in unidades_por_encaixe.items():
            encaixe = agendas[encaixe_id]
            fontes = [
                a
                for a in agendas.values()
                if a.ativa
                and a.local_id_sgg in unidades
                and a.id_sgg not in monitoradas
                and a.id_sgg not in encaixes
            ]
            candidatos = self._candidatos(fontes, hoje, resultado)
            if not candidatos:
                continue

            # Quem já tem agendamento no encaixe hoje (SGG) ou já foi tratado (livro-razão).
            existentes = {
                a.paciente_id_sgg for a in self._sgg.listar_agendamentos_da_agenda(encaixe_id, hoje)
            }
            with self._uow as uow:
                tratados = uow.encaixes_automaticos.situacoes_do_dia(hoje, encaixe_id)

            for func_id, (origem_ag, fonte) in candidatos.items():
                if func_id in existentes or func_id in tratados:
                    resultado.ja_existiam += 1
                    continue
                if not origem_ag.empresa_id_sgg:
                    resultado.sem_cadastro += 1
                    continue
                inclusao = InclusaoDTO(func_id, fonte.nome, encaixe.nome, origem_ag.id_sgg)
                if simular:
                    resultado.incluidos.append(inclusao)
                    continue
                if criados >= self._max:
                    resultado.adiados += 1
                    continue
                if criados and self._pausa:
                    time.sleep(self._pausa)  # respeita o limite de requisições do SGG
                if self._incluir(encaixe, origem_ag, fonte, agora, hoje, inclusao, resultado):
                    criados += 1

        dto = resultado.dto()
        logger.info(
            "Encaixe automático%s: %d incluídos, %d já existiam, %d sem cadastro, "
            "%d recusados, %d adiados",
            " (simulação)" if simular else "",
            len(dto.incluidos),
            dto.ja_existiam,
            dto.sem_cadastro,
            dto.recusados,
            dto.adiados,
        )
        return dto

    def _candidatos(self, fontes: list[Agenda], hoje, resultado: _Acumulador):
        """Um agendamento por pessoa (o mais cedo), entre todas as agendas-fonte."""
        por_pessoa: dict[str, tuple[Agendamento, Agenda]] = {}
        for fonte in fontes:
            try:
                itens = self._sgg.listar_agendamentos_da_agenda(fonte.id_sgg, hoje)
            except SggOperacaoRecusadaError as exc:
                resultado.avisos.append(f"{fonte.nome}: falha ao consultar ({exc}).")
                continue
            for ag in itens:
                if ag.status != StatusAgendamento.AGENDADO:
                    continue
                if not ag.paciente_id_sgg:
                    resultado.sem_cadastro += 1  # agendamento de pessoa não cadastrada
                    continue
                atual = por_pessoa.get(ag.paciente_id_sgg)
                if atual is None or (ag.data_hora, ag.id_sgg) < (
                    atual[0].data_hora,
                    atual[0].id_sgg,
                ):
                    por_pessoa[ag.paciente_id_sgg] = (ag, fonte)
        return dict(sorted(por_pessoa.items(), key=lambda kv: (kv[1][0].data_hora, kv[0])))

    def _incluir(self, encaixe, origem_ag, fonte, agora, hoje, inclusao, resultado) -> bool:
        func_id = origem_ag.paciente_id_sgg
        try:
            novo_id = self._sgg.registrar_agendamento(
                func_id,
                origem_ag.empresa_id_sgg,
                encaixe.id_sgg,
                agora,
                f"Encaixe automático (origem: {fonte.nome})",
            )
        except SggOperacaoRecusadaError as exc:
            if exc.codigo_sgg == JA_POSSUI_AGENDAMENTO:
                self._registrar(hoje, encaixe, func_id, "JA_EXISTIA", origem_ag, None, str(exc))
                resultado.ja_existiam += 1
                return False
            self._registrar(
                hoje, encaixe, func_id, "RECUSADO", origem_ag, None, str(exc), sucesso=False
            )
            resultado.recusados += 1
            return False
        # SggIndisponivelError propaga: a execução para e tenta de novo no próximo ciclo.
        except SggIndisponivelError:
            raise
        self._registrar(hoje, encaixe, func_id, "CRIADO", origem_ag, novo_id, None, fonte=fonte)
        resultado.incluidos.append(inclusao)
        return True

    def _registrar(
        self,
        hoje,
        encaixe,
        func_id,
        situacao,
        origem_ag,
        criado_id,
        detalhe,
        *,
        sucesso=True,
        fonte=None,
    ) -> None:
        with self._uow as uow:
            uow.encaixes_automaticos.registrar(
                hoje, encaixe.id_sgg, func_id, situacao, origem_ag.id_sgg, criado_id, detalhe
            )
            if situacao != "JA_EXISTIA":
                if sucesso:
                    mensagem = (
                        f"Incluído no encaixe a partir de {fonte.nome if fonte else 'outra agenda'}"
                    )
                else:
                    mensagem = f"SGG recusou a inclusão no encaixe: {detalhe}"
                uow.logs.registrar(
                    LogOperacao(
                        tipo=TipoOperacao.ENCAIXE_AUTOMATICO,
                        sucesso=sucesso,
                        mensagem=mensagem,
                        paciente_id_sgg=func_id,
                        agendamento_id_sgg=criado_id,
                        agenda_id_sgg=encaixe.id_sgg,
                        detalhes={"agendamento_origem": origem_ag.id_sgg},
                    )
                )
            uow.commit()


class _Acumulador:
    def __init__(self, simulado: bool, avisos: list[str]) -> None:
        self.simulado = simulado
        self.avisos = avisos
        self.incluidos: list[InclusaoDTO] = []
        self.ja_existiam = 0
        self.sem_cadastro = 0
        self.recusados = 0
        self.adiados = 0

    def dto(self) -> ResultadoEncaixeAutomaticoDTO:
        return ResultadoEncaixeAutomaticoDTO(
            simulado=self.simulado,
            incluidos=self.incluidos,
            ja_existiam=self.ja_existiam,
            sem_cadastro=self.sem_cadastro,
            recusados=self.recusados,
            adiados=self.adiados,
            avisos=self.avisos,
        )
