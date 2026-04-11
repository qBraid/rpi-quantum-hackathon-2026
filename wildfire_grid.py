"""
wildfire_grid.py — shared grid definition used by all wildfire scripts.

Grid values:
  0 = Empty (rock, clearing — no vegetation, fire cannot spread here)
  1 = Dry Brush (flammable — fire spreads between adjacent Dry Brush cells)
  2 = Toyon (fire-resistant — placed by optimizer, blocks fire spread)

Design choices:
  - 65% Dry Brush coverage (realistic hillside)
  - Fixed seed=42 for reproducibility across all scripts
  - Gaussian filter creates spatially correlated vegetation patches
  - Toyons can be placed on any cell (empty or dry brush)
  - Fire edges only exist between adjacent Dry Brush cells
"""

import numpy as np
from scipy.ndimage import gaussian_filter

FULL_GRID       = 10
DRY_BRUSH_PROB  = 0.65
GRID_SEED       = 42
K_GLOBAL        = 10    # total Toyon budget for the full 10x10 grid

def generate_grid(grid_size=FULL_GRID, dry_brush_prob=DRY_BRUSH_PROB,
                  seed=GRID_SEED):
    """
    Generate a realistic hillside grid using Gaussian-smoothed random noise.
    Returns binary array: 1=Dry Brush, 0=Empty.
    Gaussian filter (sigma=1.5) creates spatial vegetation clusters.
    """
    rng = np.random.RandomState(seed)
    raw = rng.random((grid_size, grid_size))
    smoothed = gaussian_filter(raw, sigma=1.5)
    threshold = np.percentile(smoothed, (1 - dry_brush_prob) * 100)
    return (smoothed > threshold).astype(int)

def get_edges(grid, grid_size=FULL_GRID):
    """
    Return all edges (i, j) where both cells are Dry Brush and adjacent.
    Only right + down neighbors to avoid double-counting.
    """
    edges = []
    for r in range(grid_size):
        for c in range(grid_size):
            if grid[r, c] != 1:
                continue
            idx = r * grid_size + c
            if c + 1 < grid_size and grid[r, c+1] == 1:
                edges.append((idx, r*grid_size + c+1))
            if r + 1 < grid_size and grid[r+1, c] == 1:
                edges.append((idx, (r+1)*grid_size + c))
    return edges

def fire_spread_count(solution, grid, grid_size=FULL_GRID):
    """
    Count active fire paths: edges between adjacent Dry Brush cells
    that are NOT blocked by a Toyon (solution[i]=1).
    solution: array of length grid_size^2, 1=Toyon placed, 0=not placed
    """
    total = 0
    for r in range(grid_size):
        for c in range(grid_size):
            if grid[r, c] != 1:
                continue
            idx = r * grid_size + c
            if solution[idx] == 1:  # Toyon here — no fire out
                continue
            if c + 1 < grid_size and grid[r, c+1] == 1 and solution[idx+1] == 0:
                total += 1
            if r + 1 < grid_size and grid[r+1, c] == 1 and solution[idx+grid_size] == 0:
                total += 1
    return total

def subgrid_info(grid, row_start, col_start, sub_grid=5,
                 full_grid=FULL_GRID):
    """
    Return cells, local edges, and boundary indices for a subgrid.
    Respects the realistic grid — only Dry Brush edges are included.
    """
    cells = []
    for r in range(sub_grid):
        for c in range(sub_grid):
            gr, gc = row_start + r, col_start + c
            cells.append(gr * full_grid + gc)

    cell_set = {c: i for i, c in enumerate(cells)}
    cell_list = set(cells)

    # Internal edges — both cells in subgrid and both Dry Brush
    edges = []
    for local_i, global_i in enumerate(cells):
        r, c = divmod(global_i, full_grid)
        for dr, dc in [(0, 1), (1, 0)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < full_grid and 0 <= nc < full_grid:
                nb = nr*full_grid + nc
                if nb in cell_set and grid[r, c] == 1 and grid[nr, nc] == 1:
                    edges.append((local_i, cell_set[nb]))

    # Boundary cells — have at least one neighbor outside this subgrid
    boundary = []
    for local_i, global_i in enumerate(cells):
        r, c = divmod(global_i, full_grid)
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < full_grid and 0 <= nc < full_grid:
                nb = nr*full_grid + nc
                if nb not in cell_list:
                    boundary.append(local_i)
                    break

    return cells, edges, boundary

def max_possible_fire_spread(grid, grid_size=FULL_GRID):
    """Total edges between Dry Brush cells (fire spread with no Toyons)."""
    empty_solution = np.zeros(grid_size**2, dtype=int)
    return fire_spread_count(empty_solution, grid, grid_size)

def greedy_marginal(grid, k_global, grid_size=FULL_GRID):
    """
    Marginal-gain greedy: iteratively place each Toyon at the cell
    that reduces fire spread the most given existing placements.
    """
    placed = np.zeros(grid_size**2, dtype=int)
    for _ in range(k_global):
        best_idx, best_delta = -1, -1
        before = fire_spread_count(placed, grid, grid_size)
        for i in range(grid_size**2):
            if placed[i] == 1:
                continue
            placed[i] = 1
            after = fire_spread_count(placed, grid, grid_size)
            placed[i] = 0
            delta = before - after
            if delta > best_delta:
                best_delta, best_idx = delta, i
        placed[best_idx] = 1
    return placed

# ── Pre-compute the shared grid and edges ─────────────────────────────────────
GRID  = generate_grid()
EDGES = get_edges(GRID)
MAX_SPREAD = max_possible_fire_spread(GRID)
DRY_BRUSH_COUNT = int(GRID.sum())

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

    print(f"Grid size:        {FULL_GRID}×{FULL_GRID} = {FULL_GRID**2} cells")
    print(f"Dry Brush cells:  {DRY_BRUSH_COUNT} "
          f"({100*DRY_BRUSH_COUNT/FULL_GRID**2:.1f}%)")
    print(f"Empty cells:      {FULL_GRID**2 - DRY_BRUSH_COUNT}")
    print(f"Fire edges:       {len(EDGES)} "
          f"(max spread with no Toyons = {MAX_SPREAD})")

    fig, ax = plt.subplots(figsize=(6, 6))
    cmap = mcolors.ListedColormap(["#e8e0d0", "#c8a96e"])
    ax.imshow(GRID.reshape(FULL_GRID, FULL_GRID),
              cmap=cmap, vmin=0, vmax=1)
    ax.set_title(f"Realistic hillside grid (seed={GRID_SEED})\n"
                 f"{DRY_BRUSH_COUNT} Dry Brush cells, "
                 f"{len(EDGES)} fire edges",
                 fontsize=10)
    ax.set_xticks(range(FULL_GRID))
    ax.set_yticks(range(FULL_GRID))
    ax.tick_params(length=0, labelsize=7)

    from matplotlib.patches import Patch
    ax.legend(
        handles=[Patch(color="#c8a96e", label="Dry Brush"),
                 Patch(color="#e8e0d0", label="Empty")],
        loc="lower center", bbox_to_anchor=(0.5, -0.08),
        ncol=2, fontsize=9
    )
    plt.tight_layout()
    plt.savefig("./wildfire_grid_preview.png", dpi=150, bbox_inches="tight")
    print("Saved → wildfire_grid_preview.png")
    plt.show()
