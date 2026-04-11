from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from problems.base import format_float


def show_wildfire_result(postprocess: dict[str, Any], *, title: str, block: bool = True) -> None:
    """Render wildfire optimization output and display it in a matplotlib window."""
    risk_map = np.asarray(postprocess.get("risk_map", []), dtype=float)
    fuel_map = np.asarray(postprocess.get("fuel_map", []), dtype=float)
    selected_cells = postprocess.get("selected_cells", [])

    if risk_map.ndim != 2 or fuel_map.ndim != 2:
        raise ValueError("Wildfire postprocess data is missing 2D risk/fuel maps for plotting.")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    risk_ax, fuel_ax = axes
    risk_img = risk_ax.imshow(risk_map, cmap="YlOrRd", origin="upper")
    risk_ax.set_title("Risk Map")
    fig.colorbar(risk_img, ax=risk_ax, fraction=0.046, pad=0.04)

    fuel_ax.imshow(fuel_map, cmap="Greens", origin="upper", vmin=0.0, vmax=1.0)
    fuel_ax.set_title("Fuel Map")

    if selected_cells:
        rows = [int(cell[0]) for cell in selected_cells]
        cols = [int(cell[1]) for cell in selected_cells]
        for ax in axes:
            ax.scatter(cols, rows, c="cyan", edgecolors="black", s=120, marker="o", label="Toyon")
            ax.legend(loc="upper right")

    for ax in axes:
        ax.set_xlabel("Column")
        ax.set_ylabel("Row")

    fire_break = postprocess.get("fire_break_score")
    fire_break_str = (
        format_float(float(fire_break))
        if isinstance(fire_break, (int, float, np.floating))
        else fire_break
    )
    fig.suptitle(f"{title} | fire_break_score={fire_break_str}")
    fig.tight_layout()
    plt.show(block=block)
    if not block:
        # Ensure non-blocking windows are painted before the next long optimization step.
        plt.pause(0.001)

