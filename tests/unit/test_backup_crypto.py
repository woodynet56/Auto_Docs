import base64
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from app.services.backup_crypto import decode_key, decrypt_backup, encrypt_backup, write_manifest


def key() -> bytes:
    return bytes(range(32))


def test_backup_round_trip_and_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source.dump"
    encrypted = tmp_path / "backup.aesgcm"
    restored = tmp_path / "restored.dump"
    manifest_path = tmp_path / "manifest.json"
    source.write_bytes(b"synthetic-postgres-custom-dump")

    manifest = encrypt_backup(source, encrypted, key())
    decrypt_backup(encrypted, restored, key())
    write_manifest(manifest, manifest_path)

    assert restored.read_bytes() == source.read_bytes()
    assert manifest.plaintext_bytes == len(source.read_bytes())
    assert "synthetic-postgres" not in encrypted.read_text(errors="ignore")
    assert "ciphertext_sha256" in manifest_path.read_text()


def test_tampered_backup_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.dump"
    encrypted = tmp_path / "backup.aesgcm"
    source.write_bytes(b"synthetic-dump")
    encrypt_backup(source, encrypted, key())
    payload = bytearray(encrypted.read_bytes())
    payload[-1] ^= 1
    encrypted.write_bytes(payload)

    with pytest.raises(InvalidTag):
        decrypt_backup(encrypted, tmp_path / "restored.dump", key())


def test_invalid_key_and_empty_backup_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        decode_key(base64.urlsafe_b64encode(b"short").decode())
    empty = tmp_path / "empty.dump"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="supported range"):
        encrypt_backup(empty, tmp_path / "backup.aesgcm", key())
