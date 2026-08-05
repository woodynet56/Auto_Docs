"""Create an encrypted PostgreSQL backup and a non-sensitive integrity manifest."""

import os
import shutil
import subprocess  # nosec B404
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.services.backup_crypto import decode_key, encrypt_backup, write_manifest


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    encoded_key = os.environ.get("BACKUP_ENCRYPTION_KEY", "")
    output_dir = Path(os.environ.get("BACKUP_OUTPUT_DIR", "backups")).resolve()
    if not database_url or not encoded_key:
        raise RuntimeError("DATABASE_URL and BACKUP_ENCRYPTION_KEY are required")
    pg_dump = shutil.which("pg_dump")
    if pg_dump is None:
        raise RuntimeError("pg_dump is required")
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    encrypted = output_dir / f"gestoria-{stamp}.dump.aesgcm"
    with tempfile.TemporaryDirectory(dir=output_dir) as temporary:
        dump = Path(temporary) / "database.dump"
        # The executable is resolved and no shell is used.
        subprocess.run(  # noqa: S603  # nosec B603
            [
                pg_dump,
                "--format=custom",
                "--no-owner",
                "--no-acl",
                "--file",
                str(dump),
                database_url,
            ],
            check=True,
            env={**os.environ, "PGAPPNAME": "gestoria-reaver-backup"},
        )
        manifest = encrypt_backup(dump, encrypted, decode_key(encoded_key))
    write_manifest(manifest, encrypted.with_suffix(encrypted.suffix + ".json"))
    print(encrypted.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
