from fastapi import APIRouter

from app.api.deps import ContainerDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health(container: ContainerDep) -> dict:
    return {"status": "ok", "sgg_mode": container.settings.sgg_mode}
