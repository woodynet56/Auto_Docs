"""Health endpoint schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "unavailable"]
    service: str
    dependencies: dict[str, Literal["ok", "unavailable"]] | None = None
