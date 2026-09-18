from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")


class SystemClock:
    def agora(self) -> datetime:
        return datetime.now(TZ)
