import os
import subprocess
import uuid

import psycopg
import pytest

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not configured")


def _sync_url() -> str:
    assert TEST_DATABASE_URL
    return TEST_DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)


def test_upgrade_constraints_and_downgrade() -> None:
    environment = {**os.environ, "DATABASE_URL": _sync_url()}
    subprocess.run(["alembic", "upgrade", "head"], check=True, env=environment)

    with psycopg.connect(_sync_url()) as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (id, phone_number, role) VALUES (%s, %s, %s)",
            (uuid.uuid4(), "+525500000001", "client"),
        )
        with pytest.raises(psycopg.errors.UniqueViolation):
            with connection.transaction():
                cursor.execute(
                    "INSERT INTO users (id, phone_number, role) VALUES (%s, %s, %s)",
                    (uuid.uuid4(), "+525500000001", "client"),
                )

    subprocess.run(["alembic", "downgrade", "base"], check=True, env=environment)
    subprocess.run(["alembic", "upgrade", "head"], check=True, env=environment)
