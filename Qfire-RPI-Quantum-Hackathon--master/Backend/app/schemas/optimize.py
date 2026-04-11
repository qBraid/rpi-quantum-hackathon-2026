from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel, Field


class OptimizationRunCreate(BaseModel):
    scenario_id: str
    mode: Literal["planning", "challenge"] = "planning"
    intervention_budget_k: int = Field(default=10, ge=10, le=10)
    reduced_candidate_count: int = Field(default=12, ge=10, le=16)


class OptimizationRunResponse(BaseModel):
    id: str
    scenario_id: str
    scenario_version: int
    status: str
    request: dict[str, Any]
    results: dict[str, Any]
    summary: dict[str, Any]
    created_at: str
