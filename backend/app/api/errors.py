from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    AgendaEncaixeNaoConfiguradaError,
    CheckinJaRealizadoError,
    ConfiguracaoInvalidaError,
    CpfInvalidoError,
    DomainError,
    PacienteNaoEncontradoError,
    SggIndisponivelError,
    SggOperacaoRecusadaError,
)

logger = logging.getLogger(__name__)

_STATUS: dict[type[DomainError], int] = {
    CpfInvalidoError: 422,
    PacienteNaoEncontradoError: status.HTTP_404_NOT_FOUND,
    CheckinJaRealizadoError: status.HTTP_409_CONFLICT,
    AgendaEncaixeNaoConfiguradaError: status.HTTP_409_CONFLICT,
    ConfiguracaoInvalidaError: status.HTTP_400_BAD_REQUEST,
    SggIndisponivelError: status.HTTP_503_SERVICE_UNAVAILABLE,
    SggOperacaoRecusadaError: status.HTTP_409_CONFLICT,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        code = _STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
        if code >= 500 or isinstance(exc, SggOperacaoRecusadaError):
            logger.error("Erro de integração: %s", exc)
        return JSONResponse(
            status_code=code, content={"codigo": exc.codigo, "mensagem": exc.mensagem}
        )

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro inesperado")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"codigo": "ERRO_INTERNO", "mensagem": "Erro interno. Tente novamente."},
        )
