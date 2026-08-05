from httpx import AsyncClient

from app.db.session import get_database_health
from app.main import app


class FakeDatabaseHealth:
    def __init__(self, ready: bool) -> None:
        self.ready = ready

    async def is_ready(self) -> bool:
        return self.ready


async def test_root_reports_current_increment(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "Gestión documental" in response.text


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "gestoria-reaver",
        "dependencies": None,
    }


async def test_readiness_when_database_is_available(client: AsyncClient) -> None:
    app.dependency_overrides[get_database_health] = lambda: FakeDatabaseHealth(True)
    try:
        response = await client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["dependencies"] == {"database": "ok"}


async def test_readiness_when_database_is_unavailable(client: AsyncClient) -> None:
    app.dependency_overrides[get_database_health] = lambda: FakeDatabaseHealth(False)
    try:
        response = await client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
