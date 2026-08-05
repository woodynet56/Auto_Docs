"""Authenticated encryption and integrity helpers for database backups."""

import base64
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT_VERSION = 1
MAX_BACKUP_BYTES = 2 * 1024 * 1024 * 1024


@dataclass(frozen=True)
class BackupManifest:
    """Non-sensitive evidence required to verify a backup artifact."""

    format_version: int
    created_at: str
    ciphertext_sha256: str
    plaintext_sha256: str
    plaintext_bytes: int


def decode_key(value: str) -> bytes:
    """Decode an exact 256-bit URL-safe base64 key."""
    try:
        key = base64.urlsafe_b64decode(value.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as error:
        raise ValueError("BACKUP_ENCRYPTION_KEY must be URL-safe base64") from error
    if len(key) != 32:
        raise ValueError("BACKUP_ENCRYPTION_KEY must decode to 32 bytes")
    return key


def encrypt_backup(source: Path, destination: Path, key: bytes) -> BackupManifest:
    """Encrypt a bounded PostgreSQL custom-format dump with AES-256-GCM."""
    size = source.stat().st_size
    if size <= 0 or size > MAX_BACKUP_BYTES:
        raise ValueError("Backup size is outside the supported range")
    plaintext = source.read_bytes()
    nonce = os.urandom(12)
    aad = f"gestoria-reaver-backup:v{FORMAT_VERSION}".encode()
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    destination.write_bytes(bytes([FORMAT_VERSION]) + nonce + ciphertext)
    manifest = BackupManifest(
        format_version=FORMAT_VERSION,
        created_at=datetime.now(UTC).isoformat(),
        ciphertext_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        plaintext_sha256=hashlib.sha256(plaintext).hexdigest(),
        plaintext_bytes=size,
    )
    return manifest


def decrypt_backup(source: Path, destination: Path, key: bytes) -> None:
    """Authenticate and decrypt a backup; fail closed on any modification."""
    payload = source.read_bytes()
    if len(payload) < 30 or payload[0] != FORMAT_VERSION:
        raise ValueError("Unsupported or truncated backup")
    nonce, ciphertext = payload[1:13], payload[13:]
    aad = f"gestoria-reaver-backup:v{FORMAT_VERSION}".encode()
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
    destination.write_bytes(plaintext)


def write_manifest(manifest: BackupManifest, destination: Path) -> None:
    """Write deterministic JSON evidence without credentials or database URLs."""
    destination.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n")
