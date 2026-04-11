from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ForecastRunCreate(BaseModel):
    scenario_id: str
    steps: int = Field(default=6, ge=2, le=12)
    dryness: float = Field(default=0.78, ge=0.0, le=1.0)
    spread_sensitivity: float = Field(default=0.64, ge=0.0, le=1.0)
    wind_speed: float = Field(default=0.58, ge=0.0, le=1.0)
    slope_influence: float = Field(default=0.42, ge=0.0, le=1.0)
    spotting_likelihood: float = Field(default=0.08, ge=0.0, le=0.3)
    ensemble_runs: int = Field(default=24, ge=8, le=64)
    seed: int = 17
    wind_direction: Literal["N", "S", "E", "W", "NE", "NW", "SE", "SW"] = "NE"


class ForecastRunResponse(BaseModel):
    id: str
    scenario_id: str
    scenario_version: int
    status: str
    request: dict[str, Any]
    snapshots: list[dict[str, Any]]
    summary: dict[str, Any]
    diagnostics: dict[str, Any]
    created_at: str
