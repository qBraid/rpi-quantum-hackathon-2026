from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class OverviewResponse(BaseModel):
    portfolio: dict[str, Any]
    recent: dict[str, Any]
    system: dict[str, Any]
