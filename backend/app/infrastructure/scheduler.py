"""Tarefas periódicas em segundo plano, sem dependências externas."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class PeriodicScheduler:
    """Executa `tarefa` (síncrona) a cada `intervalo_segundos`, numa thread."""

    def __init__(
        self,
        nome: str,
        tarefa: Callable[[], object],
        intervalo_segundos: int,
        atraso_inicial_segundos: float = 0,
        intervalo_minimo: int = 15,
    ) -> None:
        self._nome = nome
        self._tarefa = tarefa
        self._intervalo = max(intervalo_minimo, intervalo_segundos)
        self._atraso = atraso_inicial_segundos
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop(), name=self._nome)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        if self._atraso:
            await asyncio.sleep(self._atraso)
        while True:
            try:
                await asyncio.to_thread(self._tarefa)
            except Exception as exc:  # noqa: BLE001 — nunca derrubar o loop
                logger.warning("Tarefa '%s' falhou: %s", self._nome, exc)
            await asyncio.sleep(self._intervalo)
