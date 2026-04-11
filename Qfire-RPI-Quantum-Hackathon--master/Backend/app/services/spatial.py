from __future__ import annotations

from collections import deque
from typing import Iterable


STATE_BASE_RISK = {
    "empty": 0.05,
    "dry_brush": 0.88,
    "tree": 0.62,
    "water": 0.0,
    "protected": 0.18,
    "intervention": 0.12,
    "ignition": 1.0,
}


def neighbors(row: int, col: int, size: int) -> list[tuple[int, int]]:
    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    found: list[tuple[int, int]] = []
    for dr, dc in offsets:
        nr, nc = row + dr, col + dc
        if 0 <= nr < size and 0 <= nc < size:
            found.append((nr, nc))
    return found


def diagonal_neighbors(row: int, col: int, size: int) -> list[tuple[int, int]]:
    offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    found: list[tuple[int, int]] = []
    for dr, dc in offsets:
        nr, nc = row + dr, col + dc
        if 0 <= nr < size and 0 <= nc < size:
            found.append((nr, nc))
    return found


def flatten_grid(grid: list[list[str]]) -> Iterable[tuple[int, int, str]]:
    for row_idx, row in enumerate(grid):
        for col_idx, cell in enumerate(row):
            yield row_idx, col_idx, cell


def count_high_risk_components(grid: list[list[str]]) -> int:
    size = len(grid)
    seen: set[tuple[int, int]] = set()
    components = 0
    risky_states = {"dry_brush", "tree", "ignition"}
    for row, col, cell in flatten_grid(grid):
        if cell not in risky_states or (row, col) in seen:
            continue
        components += 1
        queue = deque([(row, col)])
        seen.add((row, col))
        while queue:
            cr, cc = queue.popleft()
            for nr, nc in neighbors(cr, cc, size):
                if (nr, nc) in seen or grid[nr][nc] not in risky_states:
                    continue
                seen.add((nr, nc))
                queue.append((nr, nc))
    return components


def largest_component(grid: list[list[str]]) -> int:
    size = len(grid)
    seen: set[tuple[int, int]] = set()
    best = 0
    risky_states = {"dry_brush", "tree", "ignition"}
    for row, col, cell in flatten_grid(grid):
        if cell not in risky_states or (row, col) in seen:
            continue
        count = 0
        queue = deque([(row, col)])
        seen.add((row, col))
        while queue:
            cr, cc = queue.popleft()
            count += 1
            for nr, nc in neighbors(cr, cc, size):
                if (nr, nc) in seen or grid[nr][nc] not in risky_states:
                    continue
                seen.add((nr, nc))
                queue.append((nr, nc))
        best = max(best, count)
    return best


def apply_placements(grid: list[list[str]], placements: list[dict]) -> list[list[str]]:
    updated = [row[:] for row in grid]
    for placement in placements:
        updated[placement["row"]][placement["col"]] = "intervention"
    return updated
