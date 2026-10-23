"""Composition root: monta as dependências concretas uma única vez."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.use_cases import (
    IdentificarPacienteUseCase,
    LimparDadosUseCase,
    ListarConfiguracoesUseCase,
    ListarLogsUseCase,
    ObterConfiguracaoTotemUseCase,
    RealizarCheckinUseCase,
    SalvarConfiguracaoTotemUseCase,
    SalvarConfiguracoesUseCase,
    SincronizarAgendasUseCase,
)
from app.core.config import Settings
from app.core.database import build_engine, build_session_factory, compactar_sqlite
from app.core.security import AuthService
from app.domain.ports import Clock, SggGateway
from app.infrastructure.clock import SystemClock
from app.infrastructure.persistence.migracoes import migrar_guiches_para_totem
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.scheduler import Agendador
from app.infrastructure.sgg import build_sgg_gateway


@dataclass
class Container:
    settings: Settings
    sgg: SggGateway
    clock: Clock
    auth: AuthService
    session_factory: object
    scheduler: Agendador
    engine: object

    @property
    def uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)  # type: ignore[arg-type]

    # Casos de uso são baratos de instanciar; um por request mantém isolamento.
    def identificar_paciente(self) -> IdentificarPacienteUseCase:
        return IdentificarPacienteUseCase(self.sgg, self.uow, self.clock)

    def realizar_checkin(self) -> RealizarCheckinUseCase:
        return RealizarCheckinUseCase(self.sgg, self.uow, self.clock)

    def sincronizar(self) -> SincronizarAgendasUseCase:
        return SincronizarAgendasUseCase(self.sgg, self.uow, self.clock)

    def listar_configuracoes(self) -> ListarConfiguracoesUseCase:
        return ListarConfiguracoesUseCase(self.uow)

    def salvar_configuracoes(self) -> SalvarConfiguracoesUseCase:
        return SalvarConfiguracoesUseCase(self.uow)

    def obter_totem(self) -> ObterConfiguracaoTotemUseCase:
        return ObterConfiguracaoTotemUseCase(self.uow)

    def salvar_totem(self) -> SalvarConfiguracaoTotemUseCase:
        return SalvarConfiguracaoTotemUseCase(self.uow)

    def limpar_dados(self) -> LimparDadosUseCase:
        return LimparDadosUseCase(
            self.uow, self.clock, self.settings.retencao_logs_dias, self._compactar
        )

    def _compactar(self) -> bool:
        return compactar_sqlite(self.engine)

    def listar_logs(self) -> ListarLogsUseCase:
        return ListarLogsUseCase(self.uow)


def build_container(
    settings: Settings,
    sgg: SggGateway | None = None,
    clock: Clock | None = None,
    engine=None,
) -> Container:
    engine = engine or build_engine(settings)
    if settings.auto_create_schema:
        Base.metadata.create_all(engine)
        # Sem Alembic aqui (ex.: paliativo em SQLite): aplica a mesma migração de dados.
        with engine.begin() as conn:
            migrar_guiches_para_totem(conn)
    factory = build_session_factory(engine)
    sgg = sgg or build_sgg_gateway(settings)
    clock = clock or SystemClock()
    # Cada rotina com a sua unidade de trabalho: ela guarda a sessão aberta e não pode ser
    # compartilhada entre threads.
    scheduler = Agendador(
        SincronizarAgendasUseCase(sgg, SqlAlchemyUnitOfWork(factory), clock),
        settings.sync_interval_seconds,
        LimparDadosUseCase(
            SqlAlchemyUnitOfWork(factory),
            clock,
            settings.retencao_logs_dias,
            lambda: compactar_sqlite(engine),
        ),
        clock,
    )
    return Container(
        settings=settings,
        sgg=sgg,
        clock=clock,
        auth=AuthService(settings),
        session_factory=factory,
        scheduler=scheduler,
        engine=engine,
    )
