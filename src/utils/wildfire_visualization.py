from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from problems.base import format_float


def show_wildfire_result(
    postprocess: dict[str, Any],
    *,
    title: str,
    block: bool = True,
) -> plt.Figure | None:
    """Render wildfire optimization output and display it in a matplotlib window."""
    risk_map = np.asarray(postprocess.get("risk_map", []), dtype=float)
    fuel_map = np.asarray(postprocess.get("fuel_map", []), dtype=float)
    selected_cells = postprocess.get("selected_cells", [])

    if risk_map.ndim != 2 or fuel_map.ndim != 2:
        raise ValueError("Wildfire postprocess data is missing 2D risk/fuel maps for plotting.")

    num_rows, num_cols = risk_map.shape

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("#0d1117")

    risk_ax, fuel_ax = axes
    risk_img = risk_ax.imshow(risk_map, cmap="YlOrRd", origin="upper")
    risk_ax.set_title("Risk Map", color="white")
    risk_cbar = fig.colorbar(risk_img, ax=risk_ax, fraction=0.046, pad=0.04)
    risk_cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(risk_cbar.ax.get_yticklabels(), color="white")

    fuel_ax.imshow(fuel_map, cmap="Greens", origin="upper", vmin=0.0, vmax=1.0)
    fuel_ax.set_title("Fuel Map", color="white")

    if selected_cells:
        rows = [int(cell[0]) for cell in selected_cells]
        cols = [int(cell[1]) for cell in selected_cells]
        for ax in axes:
            ax.scatter(cols, rows, c="cyan", edgecolors="black", s=120, marker="o", label="Toyon")
            legend = ax.legend(loc="upper right")
            for text in legend.get_texts():
                text.set_color("white")

    for ax in axes:
        ax.set_facecolor("#161b22")
        ax.set_xlabel("Column")
        ax.set_ylabel("Row")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("white")
        # Place one integer label at the center of each tile.
        ax.set_xticks(np.arange(num_cols))
        ax.set_yticks(np.arange(num_rows))
        ax.set_xticklabels([str(col) for col in range(num_cols)])
        ax.set_yticklabels([str(row) for row in range(num_rows)])
        ax.set_xlim(-0.5, num_cols - 0.5)
        ax.set_ylim(num_rows - 0.5, -0.5)
        # Draw visible tile borders using minor-grid ticks aligned to cell edges.
        ax.set_xticks(np.arange(-0.5, num_cols, 1.0), minor=True)
        ax.set_yticks(np.arange(-0.5, num_rows, 1.0), minor=True)
        ax.grid(which="minor", color="white", linestyle="-", linewidth=0.8, alpha=0.35)
        ax.tick_params(which="minor", bottom=False, left=False)

    fire_break = postprocess.get("fire_break_score")
    fire_break_str = (
        format_float(float(fire_break))
        if isinstance(fire_break, (int, float, np.floating))
        else fire_break
    )
    fig.suptitle(f"{title} | fire_break_score={fire_break_str}", color="white")
    fig.tight_layout()
    plt.show(block=block)
    if not block:
        # Ensure non-blocking windows are painted before the next long optimization step.
        plt.pause(0.001)
        return fig

    return None
