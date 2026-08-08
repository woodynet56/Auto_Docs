"""Restore an authenticated backup into an explicitly isolated PostgreSQL database."""

import os
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path

from app.services.backup_crypto import decode_key, decrypt_backup


def main() -> int:
    if os.environ.get("RESTORE_CONFIRM") != "RESTORE_ISOLATED_DATABASE":
        raise RuntimeError("Set RESTORE_CONFIRM=RESTORE_ISOLATED_DATABASE")
    target_url = os.environ.get("RESTORE_DATABASE_URL", "")
    source_value = os.environ.get("BACKUP_FILE", "")
    encoded_key = os.environ.get("BACKUP_ENCRYPTION_KEY", "")
    if not target_url or not source_value or not encoded_key:
        raise RuntimeError(
            "RESTORE_DATABASE_URL, BACKUP_FILE and BACKUP_ENCRYPTION_KEY are required"
        )
    pg_restore = shutil.which("pg_restore")
    if pg_restore is None:
        raise RuntimeError("pg_restore is required")
    source = Path(source_value).resolve(strict=True)
    with tempfile.TemporaryDirectory(dir=source.parent) as temporary:
        dump = Path(temporary) / "database.dump"
        decrypt_backup(source, dump, decode_key(encoded_key))
        # The executable is resolved and no shell is used.
        subprocess.run(  # noqa: S603  # nosec B603
            [
                pg_restore,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-acl",
                "--dbname",
                target_url,
                str(dump),
            ],
            check=True,
            env={**os.environ, "PGAPPNAME": "gestoria-reaver-restore-drill"},
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
