"""Liveness and readiness endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.db.session import DatabaseHealth, get_database_health
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Report whether the application process is alive."""
    return HealthResponse(status="ok", service="gestoria-reaver")


@router.get("/ready", response_model=HealthResponse)
async def readiness(
    response: Response,
    database_health: Annotated[DatabaseHealth, Depends(get_database_health)],
) -> HealthResponse:
    """Report whether required infrastructure is available."""
    if not await database_health.is_ready():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="unavailable",
            service="gestoria-reaver",
            dependencies={"database": "unavailable"},
        )

    return HealthResponse(
        status="ok",
        service="gestoria-reaver",
        dependencies={"database": "ok"},
    )
