from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Scenario


def _base_grid(fill: str = "tree") -> list[list[str]]:
    return [[fill for _ in range(10)] for _ in range(10)]


def _canyon_wind_corridor() -> list[list[str]]:
    grid = _base_grid("shrub")
    for row in range(10):
        grid[row][1] = "road_or_firebreak" if row not in {4, 5, 6} else "dry_brush"
        grid[row][8] = "road_or_firebreak"
    for row in range(2, 8):
        for col in range(3, 7):
            grid[row][col] = "dry_brush" if (row + col) % 2 == 0 else "grass"
    grid[4][4] = "ignition"
    grid[6][6] = "tree"
    grid[2][7] = "protected"
    grid[7][7] = "protected"
    return grid


def _mixed_vegetation_slope() -> list[list[str]]:
    grid = _base_grid("tree")
    for row in range(10):
        for col in range(10):
            if row <= 2 and col >= 6:
                grid[row][col] = "grass"
            elif row >= 5 and col <= 3:
                grid[row][col] = "shrub"
            elif (row + col) % 4 == 0:
                grid[row][col] = "dry_brush"
    grid[1][2] = "ignition"
    grid[8][0] = "water"
    grid[8][1] = "water"
    grid[7][8] = "road_or_firebreak"
    return grid


def _dry_ridge_treated_perimeter() -> list[list[str]]:
    grid = _base_grid("grass")
    for row in range(10):
        for col in range(10):
            if 2 <= row <= 7 and 2 <= col <= 7:
                grid[row][col] = "dry_brush" if row in {3, 4, 5} or col in {3, 6} else "shrub"
    for index in range(10):
        grid[0][index] = "protected"
        grid[9][index] = "protected"
    grid[4][5] = "ignition"
    grid[5][1] = "road_or_firebreak"
    grid[5][8] = "road_or_firebreak"
    return grid


def _patchy_wui() -> list[list[str]]:
    grid = _base_grid("empty")
    for row in range(10):
        for col in range(10):
            if row <= 5 and col <= 5:
                grid[row][col] = "grass" if (row + col) % 3 else "shrub"
            elif row >= 6 and col <= 6:
                grid[row][col] = "tree"
            elif col >= 7:
                grid[row][col] = "protected" if row in {2, 3, 6, 7} else "road_or_firebreak"
    grid[3][2] = "ignition"
    grid[8][8] = "water"
    grid[8][9] = "water"
    return grid


def _fuel_break_spotting() -> list[list[str]]:
    grid = _base_grid("shrub")
    for row in range(10):
        grid[row][4] = "road_or_firebreak"
        grid[row][5] = "road_or_firebreak"
    for row in range(1, 9):
        for col in range(6, 10):
            grid[row][col] = "dry_brush" if row % 2 == 0 else "grass"
    grid[4][2] = "ignition"
    grid[2][7] = "tree"
    grid[7][7] = "tree"
    grid[5][6] = "protected"
    return grid


def seed_sample_data(db: Session) -> None:
    existing = db.scalar(select(Scenario.id).limit(1))
    if existing:
        return

    records = [
        Scenario(
            name="Canyon Wind Corridor",
            domain="wildfire",
            status="active",
            description="Dry canyon corridor with mixed grass, shrub, and treated pockets under strong directional wind.",
            grid=_canyon_wind_corridor(),
            metadata_json={"region": "Foothill canyon", "owner": "Wildfire West"},
            constraints_json={"intervention_budget_k": 10, "crew_limit": 3, "time_horizon_hours": 72, "dryness": 0.84, "wind_speed": 0.74, "wind_direction": "NE", "spread_sensitivity": 0.69, "spotting_likelihood": 0.11},
            objectives_json={"primary": "reduce likely canyon spread corridor", "secondary": "protect treated east shoulder"},
        ),
        Scenario(
            name="Mixed Vegetation Slope",
            domain="wildfire",
            status="draft",
            description="Irregular slope with grass, shrub, tree, and brush patches that generate uneven spread pressure.",
            grid=_mixed_vegetation_slope(),
            metadata_json={"region": "Mixed slope", "owner": "Resilience Lab"},
            constraints_json={"intervention_budget_k": 10, "crew_limit": 3, "time_horizon_hours": 72, "dryness": 0.72, "wind_speed": 0.48, "wind_direction": "E", "spread_sensitivity": 0.61, "spotting_likelihood": 0.07},
            objectives_json={"primary": "delay uphill ignition progression", "secondary": "protect lower-slope breaks"},
        ),
        Scenario(
            name="Dry Ridge Treated Perimeter",
            domain="wildfire",
            status="draft",
            description="Dry interior ridge with a treated perimeter that can still be stressed by internal fuel continuity.",
            grid=_dry_ridge_treated_perimeter(),
            metadata_json={"region": "Dry ridge", "owner": "Operations"},
            constraints_json={"intervention_budget_k": 10, "crew_limit": 4, "time_horizon_hours": 96, "dryness": 0.88, "wind_speed": 0.55, "wind_direction": "SW", "spread_sensitivity": 0.66, "spotting_likelihood": 0.09},
            objectives_json={"primary": "reinforce perimeter while breaking interior connectivity"},
        ),
        Scenario(
            name="Patchy Wildland Urban Interface",
            domain="wildfire",
            status="draft",
            description="Patchy suburban interface with irregular fuels, hardened strips, and sensitive edge exposure.",
            grid=_patchy_wui(),
            metadata_json={"region": "WUI edge", "owner": "Community Planning"},
            constraints_json={"intervention_budget_k": 10, "crew_limit": 5, "time_horizon_hours": 72, "dryness": 0.69, "wind_speed": 0.52, "wind_direction": "SE", "spread_sensitivity": 0.57, "spotting_likelihood": 0.06},
            objectives_json={"primary": "protect interface edge", "secondary": "reduce ember exposure into treated edge"},
        ),
        Scenario(
            name="Fuel Break Under Spotting Stress",
            domain="wildfire",
            status="draft",
            description="Fuel break scenario where ember spotting can leap narrow breaks and create secondary ignitions.",
            grid=_fuel_break_spotting(),
            metadata_json={"region": "Fuel break testbed", "owner": "Research Ops"},
            constraints_json={"intervention_budget_k": 10, "crew_limit": 3, "time_horizon_hours": 72, "dryness": 0.8, "wind_speed": 0.67, "wind_direction": "E", "spread_sensitivity": 0.65, "spotting_likelihood": 0.14},
            objectives_json={"primary": "maintain break integrity under spotting", "secondary": "delay secondary ignition clusters"},
        ),
    ]
    db.add_all(records)
    db.commit()
