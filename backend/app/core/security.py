"""Autenticação do painel administrativo (JWT) e chave do totem."""

from __future__ import annotations

import hmac
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def verify_admin_credentials(self, username: str, password: str) -> bool:
        s = self._settings
        return hmac.compare_digest(username, s.admin_username) and hmac.compare_digest(
            password, s.admin_password
        )

    def create_access_token(self, subject: str) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(minutes=self._settings.jwt_expires_minutes),
            "role": "admin",
        }
        return jwt.encode(payload, self._settings.jwt_secret, algorithm="HS256")

    def decode_token(self, token: str) -> dict:
        return jwt.decode(token, self._settings.jwt_secret, algorithms=["HS256"])

    def verify_totem_key(self, provided: str | None) -> bool:
        expected = self._settings.totem_api_key
        if not expected:
            return True
        return provided is not None and hmac.compare_digest(provided, expected)
