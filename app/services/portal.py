"""Passwordless portal grants with hashed credentials and revocation."""

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document
from app.db.models.enums import DocumentStatus, PortalGrantStatus
from app.db.models.portal_access import DocumentDownloadEvent, PortalAccessGrant


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def new_portal_token() -> str:
    return secrets.token_urlsafe(32)


def new_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def otp_digest(otp: str, token: str) -> str:
    return hmac.new(token.encode("ascii"), otp.encode("ascii"), hashlib.sha256).hexdigest()


async def issue_grant(
    session: AsyncSession, request_id: uuid.UUID, ttl_minutes: int
) -> tuple[PortalAccessGrant, str, str]:
    existing = await session.scalar(
        select(PortalAccessGrant).where(PortalAccessGrant.request_id == request_id)
    )
    token = new_portal_token()
    otp = new_otp()
    now = datetime.now(UTC)
    if existing is None:
        existing = PortalAccessGrant(request_id=request_id, token_hash=token_digest(token))
        session.add(existing)
    existing.token_hash = token_digest(token)
    existing.status = PortalGrantStatus.ACTIVE
    existing.expires_at = now + timedelta(minutes=ttl_minutes)
    existing.otp_hash = otp_digest(otp, token)
    existing.otp_attempts = 0
    existing.otp_expires_at = now + timedelta(minutes=min(ttl_minutes, 10))
    existing.otp_verified_at = None
    existing.locked_until = None
    existing.revoked_at = None
    return existing, token, otp


async def authenticate_grant(
    session: AsyncSession,
    token: str,
    now: datetime | None = None,
    *,
    require_verified: bool = True,
) -> PortalAccessGrant | None:
    if not 32 <= len(token) <= 128 or not token.isascii():
        return None
    instant = now or datetime.now(UTC)
    conditions = [
        PortalAccessGrant.token_hash == token_digest(token),
        PortalAccessGrant.status == PortalGrantStatus.ACTIVE,
        PortalAccessGrant.expires_at > instant,
        PortalAccessGrant.revoked_at.is_(None),
    ]
    if require_verified:
        conditions.append(PortalAccessGrant.otp_verified_at.is_not(None))
    grant = await session.scalar(select(PortalAccessGrant).where(*conditions))
    if grant is not None:
        grant.last_accessed_at = instant
    return grant


async def verify_otp(
    session: AsyncSession,
    token: str,
    otp: str,
    maximum_attempts: int,
    lock_minutes: int,
    now: datetime | None = None,
) -> str | None:
    instant = now or datetime.now(UTC)
    grant = await authenticate_grant(session, token, instant, require_verified=False)
    if grant is None or grant.otp_expires_at <= instant:
        return None
    if grant.locked_until is not None and grant.locked_until > instant:
        return None
    if not otp.isascii() or not otp.isdigit() or len(otp) != 6:
        return None
    if not hmac.compare_digest(grant.otp_hash, otp_digest(otp, token)):
        grant.otp_attempts += 1
        if grant.otp_attempts >= maximum_attempts:
            grant.locked_until = instant + timedelta(minutes=lock_minutes)
        await session.commit()
        return None
    session_token = new_portal_token()
    grant.otp_verified_at = instant
    grant.otp_hash = secrets.token_hex(32)
    grant.token_hash = token_digest(session_token)
    grant.otp_attempts = 0
    grant.locked_until = None
    await session.commit()
    return session_token


async def revoke_grant(session: AsyncSession, request_id: uuid.UUID) -> bool:
    grant = await session.scalar(
        select(PortalAccessGrant).where(
            PortalAccessGrant.request_id == request_id,
            PortalAccessGrant.status == PortalGrantStatus.ACTIVE,
        )
    )
    if grant is None:
        return False
    grant.status = PortalGrantStatus.REVOKED
    grant.revoked_at = datetime.now(UTC)
    await session.commit()
    return True


async def authorize_document(
    session: AsyncSession, grant: PortalAccessGrant, document_id: uuid.UUID
) -> Document | None:
    document: Document | None = await session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.request_id == grant.request_id,
            Document.status.in_([DocumentStatus.READY, DocumentStatus.DELIVERED]),
            Document.expires_at > datetime.now(UTC),
            Document.storage_key.is_not(None),
        )
    )
    return document


def record_download(
    session: AsyncSession,
    grant: PortalAccessGrant,
    document: Document,
    outcome: str = "authorized",
) -> None:
    session.add(
        DocumentDownloadEvent(
            grant_id=grant.id,
            request_id=grant.request_id,
            document_id=document.id,
            outcome=outcome,
        )
    )
