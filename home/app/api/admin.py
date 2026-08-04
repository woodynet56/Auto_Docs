"""Minimal operational API with secret-token authentication and sanitized output."""

import hmac
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus
from app.db.models.request import ServiceRequest
from app.db.session import get_session

router = APIRouter(prefix="/admin", tags=["admin"], include_in_schema=False)


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    expected = settings.ADMIN_API_TOKEN.get_secret_value()
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not expected or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autorizado")


@router.get("/resumen", dependencies=[Depends(require_admin)])
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


@router.get("/cuarentena", dependencies=[Depends(require_admin)])
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


@router.post("/documentos/{document_id}/rechazar", dependencies=[Depends(require_admin)])
async def reject_quarantined_document(
    document_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
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
