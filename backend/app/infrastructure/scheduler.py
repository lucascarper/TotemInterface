"""Rotinas em segundo plano, sem dependências externas: sincronização com o SGG (RF01) e
limpeza diária do banco local."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta

from app.application.use_cases import LimparDadosUseCase, SincronizarAgendasUseCase
from app.domain.ports import Clock

logger = logging.getLogger(__name__)

HORA_LIMPEZA = time(3, 0)
DOMINGO = 6


def segundos_ate(agora: datetime, alvo: time) -> float:
    proximo = datetime.combine(agora.date(), alvo, agora.tzinfo)
    if proximo <= agora:
        proximo += timedelta(days=1)
    return (proximo - agora).total_seconds()


class Agendador:
    def __init__(
        self,
        sincronizar: SincronizarAgendasUseCase,
        intervalo_segundos: int,
        limpar: LimparDadosUseCase,
        clock: Clock,
    ) -> None:
        self._sincronizar = sincronizar
        self._intervalo = max(15, intervalo_segundos)
        self._limpar = limpar
        self._clock = clock
        self._tasks: list[asyncio.Task] = []
        # Uma rotina de cada vez: o VACUUM do SQLite falha com outra transação aberta.
        self._uma_por_vez = asyncio.Lock()

    async def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self._loop_sincronizacao(), name="sgg-sync"),
            asyncio.create_task(self._loop_limpeza(), name="limpeza"),
        ]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _loop_sincronizacao(self) -> None:
        while True:
            try:
                async with self._uma_por_vez:
                    await asyncio.to_thread(self._sincronizar.executar)
            except Exception as exc:  # noqa: BLE001 — nunca derrubar o loop
                logger.warning("Sincronização falhou: %r", exc)
            await asyncio.sleep(self._intervalo)

    async def _loop_limpeza(self) -> None:
        # Também roda ao iniciar: o PC da recepção pode estar desligado às 03:00.
        compactar = True
        while True:
            try:
                async with self._uma_por_vez:
                    await asyncio.to_thread(self._limpar.executar, compactar)
            except Exception as exc:  # noqa: BLE001 — nunca derrubar o loop
                logger.warning("Limpeza falhou: %r", exc)
            await asyncio.sleep(segundos_ate(self._clock.agora(), HORA_LIMPEZA))
            compactar = self._clock.agora().weekday() == DOMINGO
