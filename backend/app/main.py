from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.container import Container, build_container
from app.api.errors import register_error_handlers
from app.api.routers import admin, health, totem
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container or build_container(settings)
        if settings.app_env != "test":
            for agendador in app.state.container.schedulers:
                await agendador.start()
        logger.info("Totem API iniciada (SGG_MODE=%s)", settings.sgg_mode)
        yield
        if settings.app_env != "test":
            for agendador in app.state.container.schedulers:
                await agendador.stop()

    app = FastAPI(
        title="MultiLife · Totem de Recepção",
        version="0.1.0",
        description="API intermediária entre o totem de autoatendimento e o SGG.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=settings.cors_origin_regex_efetivo,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(totem.router)
    app.include_router(admin.router)
    return app


app = create_app()
