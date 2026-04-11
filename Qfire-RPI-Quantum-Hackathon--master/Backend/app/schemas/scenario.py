from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import BaseRecord, CellState


class ScenarioBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    domain: str = "wildfire"
    status: str = "draft"
    description: str = ""
    grid: list[list[CellState]]
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    constraints_json: dict[str, Any] = Field(default_factory=dict)
    objectives_json: dict[str, Any] = Field(default_factory=dict)


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    description: str | None = None
    grid: list[list[CellState]] | None = None
    metadata_json: dict[str, Any] | None = None
    constraints_json: dict[str, Any] | None = None
    objectives_json: dict[str, Any] | None = None
    archived: bool | None = None


class ScenarioResponse(BaseRecord, ScenarioBase):
    version: int
    archived: bool
