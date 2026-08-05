"""OIDC-backed administrative sessions and role authorization."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, status

from app.core.config import Settings


@dataclass(frozen=True)
class AdminIdentity:
    subject: str
    email: str
    roles: frozenset[str]
    csrf: str


def _fernet(settings: Settings) -> Fernet:
    raw = settings.ADMIN_SESSION_KEY.get_secret_value().encode()
    if len(raw) < 32:
        raise RuntimeError("ADMIN_SESSION_KEY must contain at least 32 characters")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw).digest()))


def encode_state(settings: Settings, nonce: str) -> str:
    payload = json.dumps({"n": nonce, "e": int(time.time()) + 600})
    body = base64.urlsafe_b64encode(payload.encode()).decode()
    signature = hmac.new(
        settings.ADMIN_SESSION_KEY.get_secret_value().encode(), body.encode(), hashlib.sha256
    ).hexdigest()
    return f"{body}.{signature}"


def decode_state(settings: Settings, value: str) -> dict[str, object]:
    try:
        body, supplied = value.rsplit(".", 1)
        expected = hmac.new(
            settings.ADMIN_SESSION_KEY.get_secret_value().encode(), body.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            raise ValueError
        data: dict[str, object] = json.loads(base64.urlsafe_b64decode(body))
        if int(str(data["e"])) < int(time.time()):
            raise ValueError
        return data
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Estado SSO inválido") from exc


def authorization_url(settings: Settings, state: str, redirect_uri: str) -> str:
    if not settings.OIDC_ISSUER_URL or not settings.OIDC_CLIENT_ID:
        raise RuntimeError("OIDC is not configured")
    query = urlencode(
        {
            "client_id": settings.OIDC_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": "openid email profile groups",
            "state": state,
        }
    )
    return f"{settings.OIDC_ISSUER_URL.rstrip('/')}/authorize?{query}"


async def exchange_code(
    settings: Settings, code: str, redirect_uri: str
) -> tuple[str, str, frozenset[str]]:
    if not settings.OIDC_ISSUER_URL or not settings.OIDC_CLIENT_ID:
        raise RuntimeError("OIDC is not configured")
    base = settings.OIDC_ISSUER_URL.rstrip("/")
    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(
            f"{base}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.OIDC_CLIENT_ID,
                "client_secret": settings.OIDC_CLIENT_SECRET.get_secret_value(),
            },
        )
        token_response.raise_for_status()
        access_token = str(token_response.json()["access_token"])
        user_response = await client.get(
            f"{base}/userinfo", headers={"Authorization": f"Bearer {access_token}"}
        )
        user_response.raise_for_status()
    claims = user_response.json()
    subject, email = str(claims.get("sub", "")), str(claims.get("email", ""))
    groups = {str(group) for group in claims.get("groups", [])}
    if not subject or not email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Identidad SSO incompleta")
    roles: set[str] = set()
    if settings.OIDC_VIEWER_GROUP in groups:
        roles.add("viewer")
    if settings.OIDC_OPERATOR_GROUP in groups:
        roles.update(("viewer", "operator"))
    if settings.OIDC_ADMIN_GROUP in groups:
        roles.update(("viewer", "operator", "security_admin"))
    if not roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin rol administrativo")
    return subject, email, frozenset(roles)


def create_session(settings: Settings, subject: str, email: str, roles: frozenset[str]) -> str:
    payload = {
        "sub": subject,
        "email": email,
        "roles": sorted(roles),
        "csrf": secrets.token_urlsafe(24),
        "exp": int(time.time()) + settings.ADMIN_SESSION_TTL_MINUTES * 60,
    }
    return _fernet(settings).encrypt(json.dumps(payload).encode()).decode()


def read_session(settings: Settings, token: str | None) -> AdminIdentity:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión requerida")
    try:
        data = json.loads(_fernet(settings).decrypt(token.encode()).decode())
        if int(data["exp"]) < int(time.time()):
            raise ValueError
        return AdminIdentity(
            str(data["sub"]), str(data["email"]), frozenset(data["roles"]), str(data["csrf"])
        )
    except (InvalidToken, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida") from exc


def require_role(request: Request, settings: Settings, role: str) -> AdminIdentity:
    identity = read_session(settings, request.cookies.get("gr_admin"))
    if role not in identity.roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso insuficiente")
    return identity


def validate_csrf(request: Request, identity: AdminIdentity) -> None:
    if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), identity.csrf):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF inválido")
