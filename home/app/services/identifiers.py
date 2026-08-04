"""Validation and privacy-preserving handling of Mexican identifiers."""

import base64
import hashlib
import hmac
import re

from cryptography.fernet import Fernet, InvalidToken

from app.db.models.enums import IdentifierType

RFC_PATTERN = re.compile(r"^[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}$")
CURP_PATTERN = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])"
    r"[HM](?:AS|BC|BS|CC|CL|CM|CS|CH|DF|DG|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ|YN|ZS|NE)[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$"
)


class InvalidIdentifierError(ValueError):
    """Raised without echoing the sensitive input."""


def normalize_identifier(value: str) -> str:
    return "".join(value.upper().split())


def identify_and_validate(value: str) -> tuple[IdentifierType, str]:
    normalized = normalize_identifier(value)
    if RFC_PATTERN.fullmatch(normalized):
        return IdentifierType.RFC, normalized
    if CURP_PATTERN.fullmatch(normalized):
        return IdentifierType.CURP, normalized
    raise InvalidIdentifierError("RFC or CURP format is invalid")


def mask_identifier(value: str) -> str:
    if len(value) < 7:
        raise InvalidIdentifierError("Identifier cannot be masked")
    return f"{value[:3]}{'*' * (len(value) - 6)}{value[-3:]}"


class IdentifierProtector:
    def __init__(self, encryption_key: str, hash_key: str) -> None:
        if not encryption_key or not hash_key:
            raise RuntimeError("Identifier protection is not configured")
        try:
            self._fernet = Fernet(encryption_key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as error:
            raise RuntimeError("Identifier encryption key is invalid") from error
        self._hash_key = hash_key.encode()

    @staticmethod
    def generate_encryption_key() -> str:
        return Fernet.generate_key().decode("ascii")

    def encrypt(self, value: str) -> bytes:
        return self._fernet.encrypt(value.encode())

    def decrypt(self, token: bytes) -> str:
        try:
            return self._fernet.decrypt(token).decode()
        except (InvalidToken, UnicodeDecodeError) as error:
            raise InvalidIdentifierError("Encrypted identifier is invalid") from error

    def digest(self, value: str) -> str:
        return hmac.new(self._hash_key, value.encode(), hashlib.sha256).hexdigest()


def valid_fernet_key(value: str) -> bool:
    try:
        return len(base64.urlsafe_b64decode(value.encode())) == 32
    except (ValueError, UnicodeEncodeError):
        return False
