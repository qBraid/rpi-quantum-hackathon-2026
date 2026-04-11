from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv


TREE_MODEL_NAMES = (
    "tree_default.obj",
    "tree_oak.obj",
    "tree_pineTallA.obj",
)


def _resolve_assets_dir(assets_dir: str | Path | None) -> Path:
    if assets_dir is not None:
        return Path(assets_dir).expanduser().resolve()
    return (
        Path(__file__).resolve().parents[2]
        / "assets"
        / "kenney_nature-kit"
        / "Models"
        / "OBJ format"
    )


def _as_polydata(mesh: pv.DataSet) -> pv.PolyData:
    if isinstance(mesh, pv.PolyData):
        return mesh
    if isinstance(mesh, pv.MultiBlock):
        return mesh.combine().extract_surface().triangulate()
    return mesh.extract_surface().triangulate()


def _load_obj_diffuse_color(obj_path: Path) -> tuple[float, float, float] | None:
    mtl_path = obj_path.with_suffix(".mtl")
    if not mtl_path.exists():
        return None

    for raw_line in mtl_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("Kd "):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    r = float(parts[1])
                    g = float(parts[2])
                    b = float(parts[3])
                except ValueError:
                    return None
                return (float(np.clip(r, 0.0, 1.0)), float(np.clip(g, 0.0, 1.0)), float(np.clip(b, 0.0, 1.0)))
    return None


def _load_tree_meshes(assets_dir: Path) -> list[tuple[pv.PolyData, tuple[float, float, float] | None]]:
    meshes: list[tuple[pv.PolyData, tuple[float, float, float] | None]] = []
    for name in TREE_MODEL_NAMES:
        obj_path = assets_dir / name
        mesh = _as_polydata(pv.read(obj_path))
        # Kenney OBJ assets are often authored with Y-up; rotate so tree height aligns with Z-up.
        x_span = mesh.bounds[1] - mesh.bounds[0]
        y_span = mesh.bounds[3] - mesh.bounds[2]
        z_span = mesh.bounds[5] - mesh.bounds[4]
        dominant_axis = int(np.argmax([x_span, y_span, z_span]))
        if dominant_axis == 0:
            mesh = mesh.rotate_y(90.0, inplace=False)
        elif dominant_axis == 1:
            mesh = mesh.rotate_x(90.0, inplace=False)

        bounds = mesh.bounds
        cx = 0.5 * (bounds[0] + bounds[1])
        cy = 0.5 * (bounds[2] + bounds[3])
        min_z = bounds[4]
        mesh = mesh.translate((-cx, -cy, -min_z), inplace=False)
        z_span = max(mesh.bounds[5] - mesh.bounds[4], 1e-6)
        mesh = mesh.scale(0.85 / z_span, inplace=False)
        meshes.append((mesh, _load_obj_diffuse_color(obj_path)))
    return meshes


def show_wildfire_result_3d(
    postprocess: dict[str, Any],
    *,
    title: str = "Wildfire Shrub Placement (3D)",
    assets_dir: str | Path | None = None,
    block: bool = True,
    screenshot_path: str | Path | None = None,
) -> None:
    """Render an artistic 3D shrub-placement scene with model trees on selected tiles."""
    risk_map = np.asarray(postprocess.get("risk_map", []), dtype=float)
    fuel_map = np.asarray(postprocess.get("fuel_map", []), dtype=float)
    selected_cells = postprocess.get("selected_cells", [])

    if risk_map.ndim != 2 or fuel_map.ndim != 2 or risk_map.shape != fuel_map.shape:
        raise ValueError("Expected 2D risk_map and fuel_map with matching shapes.")

    rows, cols = risk_map.shape
    risk_min = float(np.min(risk_map))
    risk_max = float(np.max(risk_map))
    risk_span = max(risk_max - risk_min, 1e-9)

    cmap = plt.get_cmap("Greens")
    plotter = pv.Plotter(window_size=(1400, 900), off_screen=bool(screenshot_path and not block))
    plotter.set_background("#1c1f26", top="#0f1115")

    for r in range(rows):
        for c in range(cols):
            norm_risk = float((risk_map[r, c] - risk_min) / risk_span)
            tile_color = cmap(0.35 + 0.6 * norm_risk)[:3]
            elevation = 0.03 + 0.07 * float(np.clip(fuel_map[r, c], 0.0, 1.0))
            tile = pv.Cube(
                center=(float(c), float(rows - 1 - r), elevation * 0.5),
                x_length=0.96,
                y_length=0.96,
                z_length=elevation,
            )
            plotter.add_mesh(tile, color=tile_color, smooth_shading=True)

    assets_path = _resolve_assets_dir(assets_dir)
    tree_meshes = _load_tree_meshes(assets_path)

    seen: set[tuple[int, int]] = set()
    for idx, cell in enumerate(selected_cells):
        if not isinstance(cell, (list, tuple)) or len(cell) < 2:
            continue
        r = int(cell[0])
        c = int(cell[1])
        if (r, c) in seen or not (0 <= r < rows and 0 <= c < cols):
            continue
        seen.add((r, c))

        base_tree, tree_color = tree_meshes[idx % len(tree_meshes)]
        tree = base_tree.copy(deep=True)
        tree = tree.rotate_z(float((idx * 47) % 360), inplace=False)
        z_offset = 0.08 + 0.07 * float(np.clip(fuel_map[r, c], 0.0, 1.0))
        tree = tree.translate((float(c), float(rows - 1 - r), z_offset), inplace=False)

        add_kwargs: dict[str, Any] = {
            "smooth_shading": True,
            "ambient": 0.2,
            "diffuse": 0.75,
            "specular": 0.12,
        }
        if tree_color is not None:
            add_kwargs["color"] = tree_color
        plotter.add_mesh(tree, **add_kwargs)

    # Add subtle grid accents so each shrub marker sits on a visibly distinct tile.
    for r in range(rows + 1):
        y = float(r - 0.5)
        plotter.add_lines(np.array([[-0.5, y, 0.001], [cols - 0.5, y, 0.001]]), color="#2a2f39", width=1)
    for c in range(cols + 1):
        x = float(c - 0.5)
        plotter.add_lines(np.array([[x, -0.5, 0.001], [x, rows - 0.5, 0.001]]), color="#2a2f39", width=1)

    plotter.add_title(title, font_size=14, color="white")
    plotter.add_text("Forest-green risk tiles + upright tree markers", position="lower_left", font_size=10, color="white")
    plotter.camera_position = [
        (cols * 1.2, -rows * 1.4, max(rows, cols) * 1.5),
        (cols * 0.5 - 0.5, rows * 0.5 - 0.5, 0.0),
        (0.0, 0.0, 1.0),
    ]

    if screenshot_path:
        path = Path(screenshot_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        plotter.show(auto_close=False)
        plotter.screenshot(str(path))
        plotter.close()
        return

    plotter.show(auto_close=not block)



