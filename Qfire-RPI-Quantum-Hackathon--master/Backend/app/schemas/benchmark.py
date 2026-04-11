from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BenchmarkRunCreate(BaseModel):
    scenario_id: str
    optimization_run_id: str | None = None
    shots: int = Field(default=256, ge=64, le=4096)
    reduced_candidate_count: int = Field(default=8, ge=4, le=10)
    environments: list[str] = Field(default_factory=lambda: ["ideal_simulator", "noisy_simulator", "ibm_hardware"])


class BenchmarkRunResponse(BaseModel):
    id: str
    scenario_id: str
    scenario_version: int
    optimization_run_id: str | None = None
    status: str
    request: dict[str, Any]
    results: dict[str, Any]
    summary: dict[str, Any]
    availability: dict[str, Any]
    created_at: str
