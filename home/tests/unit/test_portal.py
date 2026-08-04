import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from app.db.models.enums import PortalGrantStatus
from app.db.models.portal_access import PortalAccessGrant
from app.services.portal import (
    authenticate_grant,
    authorize_document,
    issue_grant,
    new_portal_token,
    otp_digest,
    record_download,
    revoke_grant,
    token_digest,
    verify_otp,
)


class Session:
    def __init__(self, values: list[Any]) -> None:
        self.values = values
        self.added: list[Any] = []
        self.commits = 0

    async def scalar(self, statement: Any) -> Any:
        return self.values.pop(0)

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.commits += 1


async def test_issue_new_grant_hashes_token() -> None:
    session = Session([None])
    request_id = uuid.uuid4()
    grant, token, otp = await issue_grant(session, request_id, 30)  # type: ignore[arg-type]
    assert grant.request_id == request_id
    assert grant.token_hash == token_digest(token)
    assert token not in grant.token_hash
    assert grant.status == PortalGrantStatus.ACTIVE
    assert grant.otp_hash == otp_digest(otp, token)
    assert otp not in grant.otp_hash
    assert session.added == [grant]


async def test_issue_rotates_and_reactivates_existing_grant() -> None:
    grant = PortalAccessGrant(
        request_id=uuid.uuid4(),
        token_hash="a" * 64,
        status=PortalGrantStatus.REVOKED,
        expires_at=datetime.now(UTC),
        revoked_at=datetime.now(UTC),
    )
    _, token, _ = await issue_grant(Session([grant]), grant.request_id, 15)  # type: ignore[arg-type]
    assert grant.token_hash == token_digest(token)
    assert grant.status == PortalGrantStatus.ACTIVE
    assert grant.revoked_at is None


async def test_authentication_rejects_invalid_and_accepts_active() -> None:
    assert await authenticate_grant(Session([]), "short") is None  # type: ignore[arg-type]
    token = new_portal_token()
    now = datetime.now(UTC)
    grant: Any = SimpleNamespace(last_accessed_at=None, otp_verified_at=now)
    authenticated = await authenticate_grant(Session([grant]), token, now)  # type: ignore[arg-type]
    assert authenticated is not None
    assert authenticated.last_accessed_at == now
    assert await authenticate_grant(Session([None]), token) is None  # type: ignore[arg-type]


async def test_otp_verification_and_lockout() -> None:
    token = new_portal_token()
    otp = "123456"
    now = datetime.now(UTC)
    grant: Any = SimpleNamespace(
        last_accessed_at=None,
        otp_hash=otp_digest(otp, token),
        otp_attempts=0,
        otp_expires_at=now.replace(year=now.year + 1),
        otp_verified_at=None,
        locked_until=None,
    )
    session = Session([grant])
    session_token = await verify_otp(session, token, otp, 5, 15, now)  # type: ignore[arg-type]
    assert session_token is not None
    assert grant.otp_verified_at == now
    assert grant.otp_hash != otp_digest(otp, token)
    assert grant.token_hash == token_digest(session_token)

    locked: Any = SimpleNamespace(
        last_accessed_at=None,
        otp_hash=otp_digest(otp, token),
        otp_attempts=4,
        otp_expires_at=now.replace(year=now.year + 1),
        otp_verified_at=None,
        locked_until=None,
    )
    assert await verify_otp(Session([locked]), token, "000000", 5, 15, now) is None  # type: ignore[arg-type]
    assert locked.otp_attempts == 5
    assert locked.locked_until is not None


async def test_document_authorization_and_download_record() -> None:
    request_id = uuid.uuid4()
    grant: Any = SimpleNamespace(id=uuid.uuid4(), request_id=request_id)
    document: Any = SimpleNamespace(id=uuid.uuid4(), request_id=request_id)
    session = Session([document])
    authorized = await authorize_document(session, grant, document.id)  # type: ignore[arg-type]
    assert authorized is not None
    record_download(session, grant, authorized)  # type: ignore[arg-type]
    event = session.added[0]
    assert event.document_id == document.id
    assert event.outcome == "authorized"


async def test_revoke_grant_invalidates_active_access() -> None:
    grant = SimpleNamespace(status=PortalGrantStatus.ACTIVE, revoked_at=None)
    session = Session([grant])
    assert await revoke_grant(session, uuid.uuid4())  # type: ignore[arg-type]
    assert grant.status == PortalGrantStatus.REVOKED
    assert grant.revoked_at is not None
    assert session.commits == 1
    assert not await revoke_grant(Session([None]), uuid.uuid4())  # type: ignore[arg-type]
