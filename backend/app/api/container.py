"""Composition root: monta as dependências concretas uma única vez."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.use_cases import (
    IdentificarPacienteUseCase,
    ListarConfiguracoesUseCase,
    ListarLogsUseCase,
    RealizarCheckinUseCase,
    SalvarConfiguracoesUseCase,
    SincronizarAgendasUseCase,
)
from app.core.config import Settings
from app.core.database import build_engine, build_session_factory
from app.core.security import AuthService
from app.domain.ports import Clock, SggGateway
from app.infrastructure.clock import SystemClock
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.scheduler import SyncScheduler
from app.infrastructure.sgg import build_sgg_gateway


@dataclass
class Container:
    settings: Settings
    sgg: SggGateway
    clock: Clock
    auth: AuthService
    session_factory: object
    scheduler: SyncScheduler

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
    factory = build_session_factory(engine)
    sgg = sgg or build_sgg_gateway(settings)
    clock = clock or SystemClock()
    uow = SqlAlchemyUnitOfWork(factory)
    scheduler = SyncScheduler(
        SincronizarAgendasUseCase(sgg, uow, clock), settings.sync_interval_seconds
    )
    return Container(
        settings=settings,
        sgg=sgg,
        clock=clock,
        auth=AuthService(settings),
        session_factory=factory,
        scheduler=scheduler,
    )
