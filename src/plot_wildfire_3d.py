from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from utils.wildfire_3d_visualization import show_wildfire_result_3d


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create an artistic 3D wildfire shrub-placement plot.")
    parser.add_argument("--grid-rows", type=int, default=10, help="Grid row count.")
    parser.add_argument("--grid-cols", type=int, default=10, help="Grid column count.")
    parser.add_argument("--shrub-budget", type=int, default=10, help="Number of shrubs to place.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for synthetic map generation.")
    parser.add_argument(
        "--assets-dir",
        default=str(
            Path(__file__).resolve().parents[1]
            / "assets"
            / "kenney_nature-kit"
            / "Models"
            / "OBJ format"
        ),
        help="Path to Kenney OBJ assets directory.",
    )
    parser.add_argument(
        "--save-image",
        default=None,
        help="Optional PNG output path. When set, render off-screen and save the scene.",
    )
    return parser


def _build_demo_postprocess(rows: int, cols: int, shrub_budget: int, seed: int) -> dict[str, object]:
    rng = np.random.default_rng(seed)
    risk_map = rng.uniform(0.0, 1.0, size=(rows, cols))
    fuel_map = np.clip(rng.normal(loc=0.65, scale=0.2, size=(rows, cols)), 0.0, 1.0)

    ranked = np.argsort((0.65 * risk_map + 0.35 * fuel_map).ravel())[::-1]
    count = max(0, min(shrub_budget, rows * cols))
    selected = ranked[:count]
    selected_cells = [(int(idx // cols), int(idx % cols)) for idx in selected]

    return {
        "risk_map": risk_map.tolist(),
        "fuel_map": fuel_map.tolist(),
        "selected_cells": selected_cells,
        "fire_break_score": float(np.sum(risk_map.ravel()[selected])) if count else 0.0,
    }


def main() -> None:
    args = build_parser().parse_args()
    postprocess = _build_demo_postprocess(
        rows=max(1, args.grid_rows),
        cols=max(1, args.grid_cols),
        shrub_budget=max(0, args.shrub_budget),
        seed=args.seed,
    )
    show_wildfire_result_3d(
        postprocess,
        title="Wildfire Shrub Placement (Artistic 3D)",
        assets_dir=args.assets_dir,
        block=args.save_image is None,
        screenshot_path=args.save_image,
    )


if __name__ == "__main__":
    main()

