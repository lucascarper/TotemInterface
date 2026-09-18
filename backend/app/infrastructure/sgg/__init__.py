from app.core.config import Settings
from app.domain.ports import SggGateway
from app.infrastructure.sgg.fake_gateway import SggFakeGateway
from app.infrastructure.sgg.http_gateway import SggHttpGateway


def build_sgg_gateway(settings: Settings) -> SggGateway:
    if settings.sgg_mode == "http":
        return SggHttpGateway(
            base_url=settings.sgg_base_url,
            api_key=settings.sgg_api_key,
            timeout=settings.sgg_timeout_seconds,
        )
    return SggFakeGateway()


__all__ = ["build_sgg_gateway", "SggFakeGateway", "SggHttpGateway"]
