"""Explicit request state-machine rules."""

from app.db.models.enums import RequestStatus

ALLOWED_TRANSITIONS: dict[RequestStatus, frozenset[RequestStatus]] = {
    RequestStatus.PENDING: frozenset(
        {RequestStatus.ASSIGNED, RequestStatus.CANCELLED, RequestStatus.BLOCKED}
    ),
    RequestStatus.ASSIGNED: frozenset(
        {RequestStatus.PROCESSING, RequestStatus.CANCELLED, RequestStatus.BLOCKED}
    ),
    RequestStatus.PROCESSING: frozenset(
        {RequestStatus.AWAITING_DOCUMENTS, RequestStatus.CANCELLED, RequestStatus.BLOCKED}
    ),
    RequestStatus.AWAITING_DOCUMENTS: frozenset(
        {RequestStatus.DOCUMENTS_RECEIVED, RequestStatus.CANCELLED, RequestStatus.BLOCKED}
    ),
    RequestStatus.DOCUMENTS_RECEIVED: frozenset(
        {
            RequestStatus.AWAITING_DOCUMENTS,
            RequestStatus.AWAITING_CONFIRMATION,
            RequestStatus.BLOCKED,
        }
    ),
    RequestStatus.AWAITING_CONFIRMATION: frozenset(
        {RequestStatus.COMPLETED, RequestStatus.DOCUMENTS_RECEIVED, RequestStatus.BLOCKED}
    ),
    RequestStatus.BLOCKED: frozenset({RequestStatus.PENDING, RequestStatus.CANCELLED}),
    RequestStatus.COMPLETED: frozenset(),
    RequestStatus.CANCELLED: frozenset(),
}


class InvalidStatusTransition(ValueError):
    """Raised when a request attempts a forbidden state change."""


def ensure_transition_allowed(current: RequestStatus, target: RequestStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStatusTransition(
            f"transition {current.value} -> {target.value} is not allowed"
        )
