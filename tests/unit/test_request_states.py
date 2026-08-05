import pytest

from app.db.models.enums import RequestStatus
from app.services.request_states import InvalidStatusTransition, ensure_transition_allowed


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (RequestStatus.PENDING, RequestStatus.ASSIGNED),
        (RequestStatus.AWAITING_DOCUMENTS, RequestStatus.DOCUMENTS_RECEIVED),
        (RequestStatus.AWAITING_CONFIRMATION, RequestStatus.COMPLETED),
        (RequestStatus.BLOCKED, RequestStatus.PENDING),
    ],
)
def test_allowed_transitions(current: RequestStatus, target: RequestStatus) -> None:
    ensure_transition_allowed(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (RequestStatus.PENDING, RequestStatus.COMPLETED),
        (RequestStatus.COMPLETED, RequestStatus.PROCESSING),
        (RequestStatus.CANCELLED, RequestStatus.PENDING),
        (RequestStatus.ASSIGNED, RequestStatus.DOCUMENTS_RECEIVED),
    ],
)
def test_forbidden_transitions(current: RequestStatus, target: RequestStatus) -> None:
    with pytest.raises(InvalidStatusTransition, match="is not allowed"):
        ensure_transition_allowed(current, target)
