"""Sincronização periódica em segundo plano (RF01), sem dependências externas."""

from __future__ import annotations

import asyncio
import logging

from app.application.use_cases import SincronizarAgendasUseCase

logger = logging.getLogger(__name__)


class SyncScheduler:
    def __init__(self, use_case: SincronizarAgendasUseCase, intervalo_segundos: int) -> None:
        self._uc = use_case
        self._intervalo = max(15, intervalo_segundos)
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop(), name="sgg-sync")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while True:
            try:
                await asyncio.to_thread(self._uc.executar)
            except Exception as exc:  # noqa: BLE001 — nunca derrubar o loop
                logger.warning("Sincronização falhou: %s", exc)
            await asyncio.sleep(self._intervalo)
