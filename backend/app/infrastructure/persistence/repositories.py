from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.entities import (
    Agenda,
    ConfiguracaoAgenda,
    LocalAtendimento,
    LogOperacao,
    TipoAtendimento,
    TipoOperacao,
)
from app.infrastructure.persistence.models import (
    AgendaModel,
    ConfiguracaoAgendaModel,
    EncaixeAutomaticoModel,
    LocalModel,
    LogOperacaoModel,
    SincronizacaoModel,
)


def _agora_utc() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite devolve datetimes sem fuso; tratamos tudo como UTC (PostgreSQL já vem com fuso)."""
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=UTC)


class SqlAgendaRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def substituir_todas(self, agendas: list[Agenda]) -> None:
        ids = {a.id_sgg for a in agendas}
        # Agendas que sumiram do SGG ficam inativas (não apagamos: mantém histórico).
        for m in self._s.scalars(select(AgendaModel)).all():
            if m.id_sgg not in ids:
                m.ativa = False
        for a in agendas:
            m = self._s.get(AgendaModel, a.id_sgg) or AgendaModel(id_sgg=a.id_sgg)
            m.nome, m.local_id_sgg, m.ativa = a.nome, a.local_id_sgg, a.ativa
            m.por_ordem_chegada = a.por_ordem_chegada
            m.duracao_padrao_minutos = a.duracao_padrao_minutos
            self._s.add(m)
        self._s.flush()

    def listar(self, apenas_ativas: bool = True) -> list[Agenda]:
        stmt = select(AgendaModel).order_by(AgendaModel.nome)
        if apenas_ativas:
            stmt = stmt.where(AgendaModel.ativa.is_(True))
        return [self._to_entity(m) for m in self._s.scalars(stmt).all()]

    def obter(self, agenda_id_sgg: str) -> Agenda | None:
        m = self._s.get(AgendaModel, agenda_id_sgg)
        return self._to_entity(m) if m else None

    @staticmethod
    def _to_entity(m: AgendaModel) -> Agenda:
        return Agenda(
            m.id_sgg,
            m.nome,
            m.local_id_sgg,
            m.ativa,
            m.por_ordem_chegada,
            m.duracao_padrao_minutos,
        )


class SqlLocalRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def substituir_todos(self, locais: list[LocalAtendimento]) -> None:
        self._s.execute(delete(LocalModel))
        self._s.add_all([LocalModel(id_sgg=x.id_sgg, nome=x.nome, ativo=x.ativo) for x in locais])
        self._s.flush()

    def listar(self) -> list[LocalAtendimento]:
        return [
            LocalAtendimento(m.id_sgg, m.nome, m.ativo)
            for m in self._s.scalars(select(LocalModel).order_by(LocalModel.nome)).all()
        ]


class SqlConfiguracaoAgendaRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def listar(self) -> list[ConfiguracaoAgenda]:
        return [self._to_entity(m) for m in self._s.scalars(select(ConfiguracaoAgendaModel)).all()]

    def listar_monitoradas(self) -> list[ConfiguracaoAgenda]:
        stmt = (
            select(ConfiguracaoAgendaModel)
            .join(AgendaModel, AgendaModel.id_sgg == ConfiguracaoAgendaModel.agenda_id_sgg)
            .where(ConfiguracaoAgendaModel.monitorada.is_(True), AgendaModel.ativa.is_(True))
            .order_by(AgendaModel.nome)
        )
        return [self._to_entity(m) for m in self._s.scalars(stmt).all()]

    def salvar_todas(self, configuracoes: list[ConfiguracaoAgenda]) -> None:
        for c in configuracoes:
            m = self._s.get(ConfiguracaoAgendaModel, c.agenda_id_sgg) or ConfiguracaoAgendaModel(
                agenda_id_sgg=c.agenda_id_sgg
            )
            m.monitorada = c.monitorada
            m.agenda_encaixe_id_sgg = c.agenda_encaixe_id_sgg
            m.encaixe_padrao = c.encaixe_padrao
            m.incluir_da_unidade = c.incluir_da_unidade
            self._s.add(m)
        self._s.flush()

    @staticmethod
    def _to_entity(m: ConfiguracaoAgendaModel) -> ConfiguracaoAgenda:
        return ConfiguracaoAgenda(
            m.agenda_id_sgg,
            m.monitorada,
            m.agenda_encaixe_id_sgg,
            m.encaixe_padrao,
            m.incluir_da_unidade,
        )


class SqlLogOperacaoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def registrar(self, log: LogOperacao) -> LogOperacao:
        m = LogOperacaoModel(
            criado_em=_agora_utc(),
            tipo=log.tipo.value,
            sucesso=log.sucesso,
            mensagem=log.mensagem,
            cpf_mascarado=log.cpf_mascarado,
            paciente_id_sgg=log.paciente_id_sgg,
            agendamento_id_sgg=log.agendamento_id_sgg,
            agenda_id_sgg=log.agenda_id_sgg,
            tipo_atendimento=log.tipo_atendimento.value if log.tipo_atendimento else None,
            detalhes=log.detalhes or {},
        )
        self._s.add(m)
        self._s.flush()
        log.id, log.criado_em = m.id, m.criado_em
        return log

    def listar_recentes(self, limite: int = 100) -> list[LogOperacao]:
        stmt = select(LogOperacaoModel).order_by(LogOperacaoModel.id.desc()).limit(limite)
        return [
            LogOperacao(
                tipo=TipoOperacao(m.tipo),
                sucesso=m.sucesso,
                mensagem=m.mensagem,
                cpf_mascarado=m.cpf_mascarado,
                paciente_id_sgg=m.paciente_id_sgg,
                agendamento_id_sgg=m.agendamento_id_sgg,
                agenda_id_sgg=m.agenda_id_sgg,
                tipo_atendimento=TipoAtendimento(m.tipo_atendimento)
                if m.tipo_atendimento
                else None,
                detalhes=m.detalhes or {},
                criado_em=_aware(m.criado_em),
                id=m.id,
            )
            for m in self._s.scalars(stmt).all()
        ]


class SqlSincronizacaoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def registrar_execucao(self, sucesso: bool, mensagem: str) -> None:
        self._s.add(
            SincronizacaoModel(executado_em=_agora_utc(), sucesso=sucesso, mensagem=mensagem)
        )
        self._s.flush()

    def ultima_execucao(self) -> dict | None:
        m = self._s.scalars(
            select(SincronizacaoModel).order_by(SincronizacaoModel.id.desc()).limit(1)
        ).first()
        if not m:
            return None
        return {
            "executado_em": _aware(m.executado_em),
            "sucesso": m.sucesso,
            "mensagem": m.mensagem,
        }


class SqlEncaixeAutomaticoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def situacoes_do_dia(self, data: date, agenda_encaixe_id_sgg: str) -> dict[str, str]:
        stmt = select(EncaixeAutomaticoModel).where(
            EncaixeAutomaticoModel.data == data,
            EncaixeAutomaticoModel.agenda_encaixe_id_sgg == agenda_encaixe_id_sgg,
        )
        return {m.funcionario_id_sgg: m.situacao for m in self._s.scalars(stmt).all()}

    def registrar(
        self,
        data: date,
        agenda_encaixe_id_sgg: str,
        funcionario_id_sgg: str,
        situacao: str,
        agendamento_origem_id_sgg: str | None = None,
        agendamento_criado_id_sgg: str | None = None,
        detalhe: str | None = None,
    ) -> bool:
        """False se a pessoa já constava nesse dia/agenda (nada é gravado)."""
        if funcionario_id_sgg in self.situacoes_do_dia(data, agenda_encaixe_id_sgg):
            return False
        self._s.add(
            EncaixeAutomaticoModel(
                data=data,
                agenda_encaixe_id_sgg=agenda_encaixe_id_sgg,
                funcionario_id_sgg=funcionario_id_sgg,
                situacao=situacao,
                agendamento_origem_id_sgg=agendamento_origem_id_sgg,
                agendamento_criado_id_sgg=agendamento_criado_id_sgg,
                detalhe=detalhe,
            )
        )
        self._s.flush()
        return True
