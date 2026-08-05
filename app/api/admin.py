"""SSO-protected operational API with RBAC and sanitized output."""

import secrets
import uuid
from html import escape
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus
from app.db.models.request import ServiceRequest
from app.db.session import get_session
from app.services.admin_identity import (
    AdminIdentity,
    authorization_url,
    create_session,
    decode_state,
    encode_state,
    exchange_code,
    read_session,
    require_role,
    validate_csrf,
)

router = APIRouter(prefix="/admin", tags=["admin"], include_in_schema=False)


def require_viewer(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminIdentity:
    return require_role(request, settings, "viewer")


def require_operator(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminIdentity:
    return require_role(request, settings, "operator")


@router.get("/login")
async def login(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    nonce = secrets.token_urlsafe(24)
    state = encode_state(settings, nonce)
    redirect_uri = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/admin/callback"
    response = RedirectResponse(authorization_url(settings, state, redirect_uri), 302)
    response.set_cookie(
        "gr_oidc_state", nonce, max_age=600, secure=True, httponly=True, samesite="lax"
    )
    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str,
    state: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    data = decode_state(settings, state)
    if not secrets.compare_digest(str(data["n"]), request.cookies.get("gr_oidc_state", "")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Estado SSO inválido")
    redirect_uri = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/admin/callback"
    subject, email, roles = await exchange_code(settings, code, redirect_uri)
    response = RedirectResponse("/admin", 303)
    response.set_cookie(
        "gr_admin",
        create_session(settings, subject, email, roles),
        max_age=settings.ADMIN_SESSION_TTL_MINUTES * 60,
        secure=True,
        httponly=True,
        samesite="strict",
        path="/admin",
    )
    response.delete_cookie("gr_oidc_state")
    return response


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    try:
        identity = read_session(settings, request.cookies.get("gr_admin"))
    except HTTPException:
        return RedirectResponse("/admin/login", 303)
    page = Path("app/templates/admin.html").read_text(encoding="utf-8")
    page = page.replace("{{ identity.email }}", escape(identity.email))
    page = page.replace("{{ identity.csrf }}", escape(identity.csrf))
    return HTMLResponse(page)


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse("/", 303)
    response.delete_cookie("gr_admin", path="/admin")
    return response


@router.get("/api/resumen", dependencies=[Depends(require_viewer)])
async def operational_summary(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, dict[str, int]]:
    request_rows = await session.execute(
        select(ServiceRequest.status, func.count()).group_by(ServiceRequest.status)
    )
    document_rows = await session.execute(
        select(Document.status, func.count()).group_by(Document.status)
    )
    return {
        "solicitudes": {str(key): count for key, count in request_rows.all()},
        "documentos": {str(key): count for key, count in document_rows.all()},
    }


@router.get("/api/cuarentena", dependencies=[Depends(require_viewer)])
async def quarantine_queue(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict[str, object]]:
    items = list(
        await session.scalars(
            select(Document)
            .where(
                Document.status.in_(
                    [
                        DocumentStatus.QUARANTINED,
                        DocumentStatus.SCAN_FAILED,
                        DocumentStatus.INFECTED,
                    ]
                )
            )
            .order_by(Document.created_at.desc())
            .limit(100)
        )
    )
    return [
        {
            "id": str(item.id),
            "estado": item.status,
            "tipo": item.mime_type,
            "bytes": item.size_bytes,
            "intentos": item.scan_attempts,
            "creado": item.created_at,
        }
        for item in items
    ]


@router.post("/api/documentos/{document_id}/rechazar")
async def reject_quarantined_document(
    document_id: uuid.UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    identity: Annotated[AdminIdentity, Depends(require_operator)],
) -> dict[str, str]:
    validate_csrf(request, identity)
    document = await session.scalar(
        select(Document).where(Document.id == document_id).with_for_update()
    )
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento inexistente")
    if document.status not in {
        DocumentStatus.QUARANTINED,
        DocumentStatus.SCAN_FAILED,
        DocumentStatus.INFECTED,
    }:
        raise HTTPException(status.HTTP_409_CONFLICT, "Estado no modificable")
    document.status = DocumentStatus.REJECTED
    document.next_scan_at = None
    await session.commit()
    return {"estado": DocumentStatus.REJECTED}
