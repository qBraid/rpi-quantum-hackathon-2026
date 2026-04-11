from __future__ import annotations

import math
from collections import Counter, deque
from dataclasses import dataclass

import numpy as np

WIND_VECTORS = {
    "N": (-1, 0),
    "S": (1, 0),
    "E": (0, 1),
    "W": (0, -1),
    "NE": (-1, 1),
    "NW": (-1, -1),
    "SE": (1, 1),
    "SW": (1, -1),
}

STATE_ALIASES = {
    "road": "road_or_firebreak",
    "firebreak": "road_or_firebreak",
    "road_or_firebreak": "road_or_firebreak",
    "brush": "shrub",
}


@dataclass(frozen=True)
class CellSemantics:
    name: str
    base_ignitability: float
    fuel_load: float
    burn_duration: int
    ember_propensity: float
    treatment_resistance: float
    spread_receptivity: float
    burnable: bool
    hard_barrier: bool = False


CELL_LIBRARY: dict[str, CellSemantics] = {
    "empty": CellSemantics("empty", 0.02, 0.0, 0, 0.0, 0.0, 0.05, False),
    "water": CellSemantics("water", 0.0, 0.0, 0, 0.0, 1.0, 0.0, False, True),
    "road_or_firebreak": CellSemantics("road_or_firebreak", 0.0, 0.0, 0, 0.0, 1.0, 0.0, False, True),
    "dry_brush": CellSemantics("dry_brush", 0.88, 0.9, 2, 0.16, 0.0, 0.95, True),
    "grass": CellSemantics("grass", 0.72, 0.55, 1, 0.12, 0.0, 0.82, True),
    "shrub": CellSemantics("shrub", 0.64, 0.62, 2, 0.1, 0.0, 0.74, True),
    "tree": CellSemantics("tree", 0.54, 0.8, 3, 0.2, 0.0, 0.66, True),
    "protected": CellSemantics("protected", 0.21, 0.18, 1, 0.03, 0.55, 0.22, True),
    "intervention": CellSemantics("intervention", 0.0, 0.0, 0, 0.0, 1.0, 0.0, False, True),
    "ignition": CellSemantics("ignition", 1.0, 1.0, 3, 0.18, 0.0, 1.0, True),
    "burned": CellSemantics("burned", 0.0, 0.0, 0, 0.0, 1.0, 0.0, False),
}


def normalize_state(state: str) -> str:
    normalized = STATE_ALIASES.get(state, state)
    return normalized if normalized in CELL_LIBRARY else "empty"


def normalize_grid(grid: list[list[str]]) -> list[list[str]]:
    return [[normalize_state(cell) for cell in row] for row in grid]


def orthogonal_neighbors(row: int, col: int, size: int) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = row + dr, col + dc
        if 0 <= nr < size and 0 <= nc < size:
            found.append((nr, nc))
    return found


def diagonal_neighbors(row: int, col: int, size: int) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        nr, nc = row + dr, col + dc
        if 0 <= nr < size and 0 <= nc < size:
            found.append((nr, nc))
    return found


def combined_neighbors(row: int, col: int, size: int) -> list[tuple[int, int]]:
    return orthogonal_neighbors(row, col, size) + diagonal_neighbors(row, col, size)


def fuel_layer(grid: list[list[str]]) -> list[list[float]]:
    normalized = normalize_grid(grid)
    return [[CELL_LIBRARY[cell].fuel_load for cell in row] for row in normalized]


def default_environment(scenario) -> dict:
    constraints = scenario.constraints_json or {}
    metadata = scenario.metadata_json or {}
    size = len(scenario.grid)
    slope_layer = metadata.get("slope_layer")
    if not slope_layer:
        slope_layer = [[round((row / max(1, size - 1)) * 0.6 + (col / max(1, size - 1)) * 0.15, 3) for col in range(size)] for row in range(size)]
    return {
        "dryness": float(constraints.get("dryness", 0.74)),
        "spread_sensitivity": float(constraints.get("spread_sensitivity", 0.64)),
        "wind_speed": float(constraints.get("wind_speed", 0.58)),
        "wind_direction": str(constraints.get("wind_direction", "NE")),
        "slope_influence": float(constraints.get("slope_influence", 0.42)),
        "spotting_likelihood": float(constraints.get("spotting_likelihood", 0.08)),
        "suppression_effectiveness": float(constraints.get("suppression_effectiveness", 0.2)),
        "ensemble_runs": int(constraints.get("ensemble_runs", 24)),
        "slope_layer": slope_layer,
    }


def build_environment(base: dict, **overrides) -> dict:
    environment = {**base}
    environment.update({key: value for key, value in overrides.items() if value is not None})
    return environment


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _wind_alignment(source: tuple[int, int], target: tuple[int, int], wind_direction: str) -> float:
    wr, wc = WIND_VECTORS[wind_direction]
    dr = target[0] - source[0]
    dc = target[1] - source[1]
    norm = math.sqrt(dr * dr + dc * dc)
    if norm == 0:
        return 0.0
    return ((dr / norm) * wr + (dc / norm) * wc + 1.0) / 2.0


def _adjacency_pressure(grid: list[list[str]], burning: set[tuple[int, int]], row: int, col: int, wind_direction: str) -> float:
    size = len(grid)
    pressure = 0.0
    for nr, nc in orthogonal_neighbors(row, col, size):
        if (nr, nc) in burning:
            pressure += 1.0 + 0.45 * _wind_alignment((nr, nc), (row, col), wind_direction)
    for nr, nc in diagonal_neighbors(row, col, size):
        if (nr, nc) in burning:
            pressure += 0.35 + 0.2 * _wind_alignment((nr, nc), (row, col), wind_direction)
    return pressure


def local_hazard_features(grid: list[list[str]], row: int, col: int, environment: dict) -> dict:
    normalized = normalize_grid(grid)
    size = len(normalized)
    state = normalized[row][col]
    semantics = CELL_LIBRARY[state]
    slope_layer = environment["slope_layer"]
    ignition_cells = [(r, c) for r, line in enumerate(normalized) for c, value in enumerate(line) if value == "ignition"]
    distance_to_ignition = min((abs(row - ir) + abs(col - ic) for ir, ic in ignition_cells), default=size * 2)
    local_cells = [normalized[nr][nc] for nr, nc in combined_neighbors(row, col, size)]
    fuel_neighbors = [CELL_LIBRARY[cell].fuel_load for cell in local_cells]
    local_fuel_density = float(sum(fuel_neighbors) / max(1, len(fuel_neighbors)))
    flammable_neighbors = sum(1 for cell in local_cells if CELL_LIBRARY[cell].burnable)
    wind_exposure = 0.0
    if ignition_cells:
        nearest = min(ignition_cells, key=lambda item: abs(item[0] - row) + abs(item[1] - col))
        wind_exposure = _wind_alignment(nearest, (row, col), environment["wind_direction"])
    centrality_proxy = sum(1 for nr, nc in orthogonal_neighbors(row, col, size) if CELL_LIBRARY[normalized[nr][nc]].burnable)
    return {
        "state": state,
        "fuel_load": semantics.fuel_load,
        "base_ignitability": semantics.base_ignitability,
        "burn_duration": semantics.burn_duration,
        "ember_propensity": semantics.ember_propensity,
        "treatment_resistance": semantics.treatment_resistance,
        "spread_receptivity": semantics.spread_receptivity,
        "distance_to_ignition": float(distance_to_ignition),
        "distance_risk": 1.0 - _clip(distance_to_ignition / max(1.0, (size - 1) * 2.0), 0.0, 1.0),
        "local_fuel_density": local_fuel_density,
        "flammable_neighbor_fraction": flammable_neighbors / max(1, len(local_cells)),
        "wind_exposure": wind_exposure,
        "slope_factor": float(slope_layer[row][col]),
        "connectivity_proxy": float(centrality_proxy / 4.0),
        "treated": 1.0 if state in {"protected", "intervention"} else 0.0,
    }


def _ignition_probability(grid: list[list[str]], burning: set[tuple[int, int]], row: int, col: int, environment: dict) -> float:
    normalized = normalize_grid(grid)
    semantics = CELL_LIBRARY[normalized[row][col]]
    features = local_hazard_features(normalized, row, col, environment)
    adjacency_pressure = _adjacency_pressure(normalized, burning, row, col, environment["wind_direction"])
    
    if adjacency_pressure <= 1e-4:
        return 0.0
        
    dryness = environment["dryness"]
    spread = environment["spread_sensitivity"]
    wind_speed = environment["wind_speed"]
    slope = environment["slope_influence"] * features["slope_factor"]
    suppression = environment["suppression_effectiveness"] * semantics.treatment_resistance

    susceptibility_linear = (
        -2.5
        + 1.8 * semantics.base_ignitability
        + 1.2 * semantics.fuel_load
        + 0.8 * features["local_fuel_density"]
        + 1.5 * dryness
        + 1.0 * spread
        + 0.8 * wind_speed * features["wind_exposure"]
        + 0.6 * slope
        - 2.5 * suppression
    )
    
    susceptibility = _sigmoid(susceptibility_linear)
    return 1.0 - math.exp(-0.8 * adjacency_pressure * susceptibility)


def _sample_environment(environment: dict, rng: np.random.Generator) -> dict:
    return {
        **environment,
        "dryness": _clip(environment["dryness"] + float(rng.normal(0.0, 0.035)), 0.2, 0.98),
        "wind_speed": _clip(environment["wind_speed"] + float(rng.normal(0.0, 0.05)), 0.1, 1.0),
        "spotting_likelihood": _clip(environment["spotting_likelihood"] + float(rng.normal(0.0, 0.015)), 0.0, 0.25),
    }


def run_stochastic_forecast(
    grid: list[list[str]],
    environment: dict,
    steps: int,
    seed: int = 17,
    runs: int = 24,
) -> dict:
    normalized = normalize_grid(grid)
    size = len(normalized)
    rng = np.random.default_rng(seed)
    burn_counts = np.zeros((size, size), dtype=float)
    ignition_time_sum = np.zeros((size, size), dtype=float)
    ignition_time_hits = np.zeros((size, size), dtype=float)
    final_burned_distribution: list[int] = []
    representative_snapshots: list[dict] | None = None
    representative_score = None
    corridor_counts: Counter[tuple[int, int]] = Counter()

    for run_idx in range(runs):
        env = _sample_environment(environment, rng)
        run_grid = [row[:] for row in normalized]
        burn_timer = np.zeros((size, size), dtype=int)
        burning = {(r, c) for r, line in enumerate(run_grid) for c, cell in enumerate(line) if cell == "ignition"}
        for row, col in burning:
            burn_timer[row, col] = CELL_LIBRARY["ignition"].burn_duration
            burn_counts[row, col] += 1
            ignition_time_sum[row, col] += 0
            ignition_time_hits[row, col] += 1

        snapshots: list[dict] = []
        for step in range(steps + 1):
            counts = Counter(cell for row in run_grid for cell in row)
            snapshots.append(
                {
                    "step": step,
                    "grid": [row[:] for row in run_grid],
                    "metrics": {
                        "burning_cells": counts.get("ignition", 0),
                        "burned_cells": counts.get("burned", 0),
                        "unburned_fuel": sum(1 for row in run_grid for cell in row if CELL_LIBRARY[cell].burnable and cell not in {"ignition", "burned"}),
                    },
                }
            )
            if step == steps:
                break

            new_ignitions: set[tuple[int, int]] = set()
            active_burning = {(row, col) for row, col in burning if run_grid[row][col] == "ignition"}
            for row in range(size):
                for col in range(size):
                    state = run_grid[row][col]
                    semantics = CELL_LIBRARY[state]
                    if state in {"ignition", "burned"} or semantics.hard_barrier or not semantics.burnable:
                        continue
                    probability = _clip(_ignition_probability(run_grid, active_burning, row, col, env), 0.0, 0.97)
                    if rng.random() < probability:
                        new_ignitions.add((row, col))

            ember_candidates = [(row, col) for row, col in active_burning if CELL_LIBRARY[run_grid[row][col]].ember_propensity > 0]
            for source in ember_candidates:
                source_semantics = CELL_LIBRARY[run_grid[source[0]][source[1]]]
                if rng.random() < env["spotting_likelihood"] * source_semantics.ember_propensity:
                    distance = int(rng.integers(2, 5))
                    angle_direction = env["wind_direction"]
                    wr, wc = WIND_VECTORS[angle_direction]
                    target = (source[0] + wr * distance + int(rng.integers(-1, 2)), source[1] + wc * distance + int(rng.integers(-1, 2)))
                    if 0 <= target[0] < size and 0 <= target[1] < size:
                        target_state = run_grid[target[0]][target[1]]
                        if CELL_LIBRARY[target_state].burnable and target_state not in {"ignition", "burned"}:
                            new_ignitions.add(target)

            updated_burning: set[tuple[int, int]] = set()
            for row, col in active_burning:
                burn_timer[row, col] -= 1
                if burn_timer[row, col] <= 0:
                    run_grid[row][col] = "burned"
                else:
                    updated_burning.add((row, col))

            for row, col in new_ignitions:
                if run_grid[row][col] in {"ignition", "burned"}:
                    continue
                run_grid[row][col] = "ignition"
                burn_timer[row, col] = max(1, CELL_LIBRARY[normalize_state(grid[row][col])].burn_duration)
                burn_counts[row, col] += 1
                ignition_time_sum[row, col] += step + 1
                ignition_time_hits[row, col] += 1
                updated_burning.add((row, col))
                corridor_counts[(row, col)] += 1
            burning = updated_burning

        final_burned = sum(1 for row in run_grid for cell in row if cell == "burned")
        final_burned_distribution.append(final_burned)
        if representative_snapshots is None or representative_score is None or abs(final_burned - np.mean(final_burned_distribution)) < representative_score:
            representative_snapshots = snapshots
            representative_score = abs(final_burned - np.mean(final_burned_distribution))

    burn_probability_map: list[dict] = []
    ignition_time_map: list[dict] = []
    score_lookup: dict[str, float] = {}
    ignition_lookup: dict[str, float | None] = {}
    for row in range(size):
        for col in range(size):
            probability = float(burn_counts[row, col] / max(1, runs))
            expected_time = None
            if ignition_time_hits[row, col] > 0:
                expected_time = float(ignition_time_sum[row, col] / ignition_time_hits[row, col])
            burn_probability_map.append({"row": row, "col": col, "probability": round(probability, 4), "state": normalized[row][col]})
            ignition_time_map.append({"row": row, "col": col, "expected_ignition_time": round(expected_time, 3) if expected_time is not None else None})
            score_lookup[f"{row}-{col}"] = round(probability, 4)
            ignition_lookup[f"{row}-{col}"] = round(expected_time, 3) if expected_time is not None else None

    distribution = np.asarray(final_burned_distribution, dtype=float)
    corridor_cells = [
        {"row": row, "col": col, "frequency": round(count / max(1, runs), 4)}
        for (row, col), count in corridor_counts.most_common(12)
    ]
    summary = {
        "ensemble_runs": runs,
        "mean_final_burned_area": round(float(distribution.mean()), 3),
        "p10_final_burned_area": round(float(np.percentile(distribution, 10)), 3),
        "p50_final_burned_area": round(float(np.percentile(distribution, 50)), 3),
        "p90_final_burned_area": round(float(np.percentile(distribution, 90)), 3),
        "peak_burn_probability": round(float(max(item["probability"] for item in burn_probability_map)), 4),
        "likely_spread_corridors": corridor_cells,
    }
    return {
        "representative_snapshots": representative_snapshots or [],
        "burn_probability_map": burn_probability_map,
        "expected_ignition_time_map": ignition_time_map,
        "burn_probability_lookup": score_lookup,
        "expected_ignition_time_lookup": ignition_lookup,
        "final_burned_area_distribution": [int(value) for value in final_burned_distribution],
        "summary": summary,
    }


def high_probability_corridors(probability_map: list[dict], threshold: float = 0.45) -> list[tuple[int, int]]:
    return [(item["row"], item["col"]) for item in probability_map if item["probability"] >= threshold]


def adjacency_metrics(grid: list[list[str]]) -> dict:
    normalized = normalize_grid(grid)
    size = len(normalized)
    flammable = {(row, col) for row, line in enumerate(normalized) for col, cell in enumerate(line) if CELL_LIBRARY[cell].burnable and cell not in {"burned"}}
    edges = set()
    for row, col in flammable:
        for nr, nc in orthogonal_neighbors(row, col, size):
            if (nr, nc) in flammable and (normalized[nr][nc] not in {"protected", "intervention"} or normalized[row][col] not in {"protected", "intervention"}):
                edges.add(tuple(sorted(((row, col), (nr, nc)))))
    seen: set[tuple[int, int]] = set()
    components = 0
    largest = 0
    for cell in flammable:
        if cell in seen:
            continue
        components += 1
        queue = deque([cell])
        seen.add(cell)
        count = 0
        while queue:
            current = queue.popleft()
            count += 1
            for nr, nc in orthogonal_neighbors(current[0], current[1], size):
                if (nr, nc) in flammable and (nr, nc) not in seen:
                    seen.add((nr, nc))
                    queue.append((nr, nc))
        largest = max(largest, count)
    return {
        "adjacency_links": len(edges),
        "components": components,
        "largest_component": largest,
        "flammable_cells": len(flammable),
    }
