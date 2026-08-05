"""Authenticated, revocable document portal."""

import hmac
import secrets
import uuid
from html import escape
from typing import Annotated
from urllib.parse import parse_qs, quote

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus
from app.db.session import get_session
from app.services.portal import authenticate_grant, authorize_document, record_download, verify_otp
from app.services.r2 import R2StorageClient, StorageError

router = APIRouter(prefix="/portal", tags=["portal"], include_in_schema=False)
COOKIE_NAME = "gr_portal_session"
CSRF_COOKIE_NAME = "gr_portal_csrf"


def _no_store(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'self'; img-src 'self'; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    )
    return response


@router.get("/acceso")
async def redeem_access(
    token: Annotated[str, Query(min_length=32, max_length=128)],
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    grant = await authenticate_grant(session, token, require_verified=False)
    if grant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Acceso inválido o vencido")
    await session.commit()
    csrf_token = secrets.token_urlsafe(24)
    response = RedirectResponse("/portal/verificar", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.PORTAL_SESSION_TTL_MINUTES * 60,
        httponly=True,
        secure=settings.PORTAL_COOKIE_SECURE,
        samesite="strict",
        path="/portal",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=600,
        httponly=False,
        secure=settings.PORTAL_COOKIE_SECURE,
        samesite="strict",
        path="/portal",
    )
    return _no_store(response)


@router.get("/verificar", response_class=HTMLResponse)
async def verification_form(
    session: Annotated[AsyncSession, Depends(get_session)],
    portal_token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
    csrf_token: Annotated[str | None, Cookie(alias=CSRF_COOKIE_NAME)] = None,
) -> Response:
    grant = await authenticate_grant(session, portal_token or "", require_verified=False)
    if grant is None or not csrf_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Acceso inválido o vencido")
    body = (
        '<!doctype html><html lang="es"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Verificar acceso | Gestoría Reaver</title>"
        '<link rel="stylesheet" href="/static/css/site.css">'
        '<main class="section container"><h1>Verifica tu acceso</h1>'
        "<p>Ingresa el código de seis dígitos enviado por WhatsApp.</p>"
        '<form method="post" action="/portal/verificar">'
        f'<input type="hidden" name="csrf" value="{escape(csrf_token)}">'
        '<label>Código<input name="codigo" inputmode="numeric" autocomplete="one-time-code" '
        'pattern="[0-9]{6}" minlength="6" maxlength="6" required></label>'
        '<button class="button" type="submit">Verificar</button></form></main></html>'
    )
    return _no_store(HTMLResponse(body))


@router.post("/verificar")
async def complete_verification(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
    portal_token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE_NAME)] = None,
) -> Response:
    if request.headers.get("content-type", "").split(";", 1)[0] != (
        "application/x-www-form-urlencoded"
    ):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Formato no permitido")
    raw = await request.body()
    if len(raw) > 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Solicitud demasiado grande")
    values = parse_qs(raw.decode("ascii", errors="ignore"), strict_parsing=False)
    csrf_form = values.get("csrf", [""])[0]
    otp = values.get("codigo", [""])[0]
    if not csrf_cookie or not hmac.compare_digest(csrf_cookie, csrf_form):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solicitud no válida")
    session_token = await verify_otp(
        session,
        portal_token or "",
        otp,
        settings.PORTAL_OTP_MAX_ATTEMPTS,
        settings.PORTAL_OTP_LOCK_MINUTES,
    )
    if session_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código inválido o vencido")
    response = RedirectResponse("/portal", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        COOKIE_NAME,
        session_token,
        max_age=settings.PORTAL_SESSION_TTL_MINUTES * 60,
        httponly=True,
        secure=settings.PORTAL_COOKIE_SECURE,
        samesite="strict",
        path="/portal",
    )
    response.delete_cookie(CSRF_COOKIE_NAME, path="/portal")
    return _no_store(response)


@router.get("", response_class=HTMLResponse)
async def portal_home(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    portal_token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> Response:
    grant = await authenticate_grant(session, portal_token or "")
    if grant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o vencida")
    documents = list(
        await session.scalars(
            select(Document)
            .where(
                Document.request_id == grant.request_id,
                Document.status.in_([DocumentStatus.READY, DocumentStatus.DELIVERED]),
            )
            .order_by(Document.created_at)
        )
    )
    await session.commit()
    rows = "".join(
        '<li class="card"><span>'
        f"{escape(item.original_filename)}</span> "
        f'<a class="button" href="/portal/documentos/{item.id}">Descargar</a></li>'
        for item in documents
        if item.storage_key is not None
    )
    body = (
        '<!doctype html><html lang="es"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Documentos seguros | Gestoría Reaver</title>"
        '<link rel="stylesheet" href="/static/css/site.css">'
        '<main id="contenido" class="section container"><h1>Documentos disponibles</h1>'
        "<p>Esta sesión es personal, temporal y puede revocarse.</p>"
        f'<ul class="cards">{rows}</ul><a href="/portal/salir">Cerrar sesión</a></main></html>'
    )
    return _no_store(HTMLResponse(body))


@router.get("/documentos/{document_id}")
async def download_document(
    document_id: uuid.UUID,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
    portal_token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> Response:
    grant = await authenticate_grant(session, portal_token or "")
    if grant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o vencida")
    document = await authorize_document(session, grant, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no disponible")
    endpoint = settings.R2_ENDPOINT_URL or ""
    bucket = settings.R2_BUCKET_NAME or ""
    access_key = settings.R2_ACCESS_KEY_ID.get_secret_value()
    secret_key = settings.R2_SECRET_ACCESS_KEY.get_secret_value()
    if not all((endpoint, bucket, access_key, secret_key)):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Almacenamiento no disponible")
    storage = R2StorageClient(endpoint, bucket, access_key, secret_key)
    try:
        content = await storage.get_private(document.storage_key or "", settings.DOCUMENT_MAX_BYTES)
    except StorageError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Documento no disponible") from exc
    record_download(session, grant, document)
    await session.commit()
    safe_name = quote(document.original_filename, safe="")
    response = Response(content, media_type=document.mime_type)
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{safe_name}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return _no_store(response)


@router.get("/salir")
async def logout() -> Response:
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(COOKIE_NAME, path="/portal")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/portal")
    return _no_store(response)
