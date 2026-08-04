"""Allow-list validation based on file signatures, not user-controlled names."""

from dataclasses import dataclass
from pathlib import PurePath


class InvalidDocument(ValueError):
    """Raised when document bytes or metadata violate the upload policy."""


@dataclass(frozen=True)
class ValidatedDocument:
    mime_type: str
    extension: str


def validate_document(data: bytes, filename: str | None, maximum_bytes: int) -> ValidatedDocument:
    if not data or len(data) > maximum_bytes:
        raise InvalidDocument("Document size is outside the allowed range")
    detected: ValidatedDocument | None = None
    if data.startswith(b"%PDF-"):
        detected = ValidatedDocument("application/pdf", ".pdf")
    elif data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"):
        detected = ValidatedDocument("image/jpeg", ".jpg")
    elif data.startswith(b"\x89PNG\r\n\x1a\n") and b"IEND" in data[-32:]:
        detected = ValidatedDocument("image/png", ".png")
    if detected is None:
        raise InvalidDocument("Unsupported or malformed document")
    if filename:
        suffix = PurePath(filename).suffix.lower()
        allowed = {detected.extension}
        if detected.extension == ".jpg":
            allowed.add(".jpeg")
        if suffix not in allowed:
            raise InvalidDocument("Filename extension does not match document content")
    return detected
