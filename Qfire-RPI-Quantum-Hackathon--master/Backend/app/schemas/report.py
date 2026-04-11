from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    scenario_id: str
    risk_run_id: str | None = None
    forecast_run_id: str | None = None
    optimization_run_id: str | None = None
    benchmark_run_id: str | None = None
    title: str = Field(default="Decision report")


class ReportResponse(BaseModel):
    id: str
    scenario_id: str
    title: str
    status: str
    sections: dict[str, Any]
    export: dict[str, Any]
    created_at: str
