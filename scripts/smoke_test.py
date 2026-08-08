"""Local smoke test that runs Uvicorn and verifies the base endpoints."""

import json
import subprocess  # noqa: S404  # nosec B404
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# This script launches only the fixed local Uvicorn command declared below.

HOST = "127.0.0.1"
PORT = 8077
BASE_URL = f"http://{HOST}:{PORT}"


def fetch(path: str) -> tuple[int, dict[str, object]]:
    try:
        # BASE_URL is the fixed loopback URL declared above.
        with urllib.request.urlopen(  # noqa: S310  # nosec B310
            f"{BASE_URL}{path}", timeout=5
        ) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def fetch_text(path: str) -> tuple[int, str]:
    # BASE_URL is the fixed loopback URL declared above.
    with urllib.request.urlopen(  # noqa: S310  # nosec B310
        f"{BASE_URL}{path}", timeout=5
    ) as response:
        return response.status, response.read().decode("utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    # Arguments are fixed and shell=False is retained.
    process = subprocess.Popen(  # noqa: S603  # nosec B603
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", HOST, "--port", str(PORT)],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(30):
            try:
                live_status, live_body = fetch("/health/live")
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        else:
            raise RuntimeError("Application did not become available")

        root_status, root_body = fetch_text("/")
        ready_status, ready_body = fetch("/health/ready")

        require(live_status == 200 and live_body["status"] == "ok", "Invalid liveness")
        require(
            root_status == 200 and "Gestión documental" in root_body,
            "Invalid root response",
        )
        require(
            ready_status == 503 and ready_body["dependencies"] == {"database": "unavailable"},
            "Readiness must fail closed without PostgreSQL",
        )
        print("Smoke test passed: root=200 live=200 ready=503 (database unavailable)")
        return 0
    finally:
        process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
