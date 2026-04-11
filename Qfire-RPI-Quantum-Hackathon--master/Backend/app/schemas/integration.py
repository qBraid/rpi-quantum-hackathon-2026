from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class IntegrationStatusResponse(BaseModel):
    provider: str
    available: bool
    mode: str
    details: dict[str, Any]
    updated_at: str


class IntegrationSummaryResponse(BaseModel):
    simulator_only: bool
    hardware_available: bool
    qbraid_ready: bool
    providers: list[IntegrationStatusResponse]
