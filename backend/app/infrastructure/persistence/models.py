from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LocalModel(Base):
    __tablename__ = "locais_atendimento"

    id_sgg: Mapped[str] = mapped_column(String(64), primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AgendaModel(Base):
    __tablename__ = "agendas"

    id_sgg: Mapped[str] = mapped_column(String(64), primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    local_id_sgg: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    por_ordem_chegada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duracao_padrao_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConfiguracaoAgendaModel(Base):
    __tablename__ = "configuracoes_agenda"

    agenda_id_sgg: Mapped[str] = mapped_column(
        String(64), ForeignKey("agendas.id_sgg", ondelete="CASCADE"), primary_key=True
    )
    monitorada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    agenda_encaixe_id_sgg: Mapped[str | None] = mapped_column(String(64), nullable=True)
    encaixe_padrao: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class LogOperacaoModel(Base):
    __tablename__ = "logs_operacao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    sucesso: Mapped[bool] = mapped_column(Boolean, nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    cpf_mascarado: Mapped[str | None] = mapped_column(String(20))
    paciente_id_sgg: Mapped[str | None] = mapped_column(String(64))
    agendamento_id_sgg: Mapped[str | None] = mapped_column(String(64))
    agenda_id_sgg: Mapped[str | None] = mapped_column(String(64))
    tipo_atendimento: Mapped[str | None] = mapped_column(String(20))
    detalhes: Mapped[dict] = mapped_column(JSON, default=dict)


class SincronizacaoModel(Base):
    __tablename__ = "sincronizacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    executado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sucesso: Mapped[bool] = mapped_column(Boolean, nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
