"""Run the repeatable Auto-Docs Torres quality gate."""

from __future__ import annotations

import argparse
import subprocess  # noqa: S404  # nosec B404
import sys
from dataclasses import dataclass
from pathlib import Path

# Commands are immutable tuples declared below and always execute with shell=False.


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]


BASE_CHECKS = (
    Check("Ruff lint", (sys.executable, "-m", "ruff", "check", ".")),
    Check("Ruff format", (sys.executable, "-m", "ruff", "format", "--check", ".")),
    Check("MyPy strict", (sys.executable, "-m", "mypy", "app", "tests")),
    Check(
        "Gherkin acceptance",
        (
            sys.executable,
            "-m",
            "pytest",
            "tests/acceptance",
            "-m",
            "acceptance",
            "--junitxml=qa-results/gherkin.xml",
        ),
    ),
    Check(
        "Regression and coverage",
        (
            sys.executable,
            "-m",
            "pytest",
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=xml:qa-results/coverage.xml",
            "--cov-fail-under=85",
        ),
    ),
    Check(
        "Bandit",
        (sys.executable, "-m", "bandit", "-c", "pyproject.toml", "-r", "app", "scripts"),
    ),
    Check("Dependency audit", (sys.executable, "-m", "pip_audit", "-r", "requirements.txt")),
    Check("Compilation", (sys.executable, "-m", "compileall", "-q", "app", "scripts")),
)

CI_CHECKS = (
    Check("Alembic migration consistency", (sys.executable, "-m", "alembic", "check")),
    Check(
        "PostgreSQL migration cycle",
        (
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_postgres_migrations.py",
            "-m",
            "integration",
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("local", "ci"),
        default="local",
        help="ci requires TEST_DATABASE_URL pointing to isolated PostgreSQL",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    Path("qa-results").mkdir(exist_ok=True)
    checks = BASE_CHECKS + (CI_CHECKS if args.profile == "ci" else ())
    for check in checks:
        print(f"\n[QUALITY GATE] {check.name}", flush=True)
        result = subprocess.run(check.command, check=False)  # noqa: S603  # nosec B603
        if result.returncode != 0:
            print(f"[NO-GO] Falló: {check.name}", file=sys.stderr)
            return result.returncode
    print("\n[GO] Todos los controles del perfil aprobaron.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
