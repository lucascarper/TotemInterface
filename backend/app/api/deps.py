from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.container import Container

_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def require_admin(
    container: ContainerDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticação necessária.")
    try:
        payload = container.auth.decode_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada.") from exc
    if payload.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão.")
    return str(payload["sub"])


def require_totem(
    container: ContainerDep,
    x_totem_key: Annotated[str | None, Header()] = None,
) -> None:
    if not container.auth.verify_totem_key(x_totem_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave do totem inválida.")
