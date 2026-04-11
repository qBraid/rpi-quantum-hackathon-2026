from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv


TREE_MODEL_NAMES = (
    "tree_default.glb",
    "tree_oak.glb",
    "tree_pineTallA.glb",
)

DRY_BUSH_MODEL_NAMES = (
    "plant_bushDetailed.glb",
    "plant_bushLarge.glb",
    "plant_bush.glb",
)


def _resolve_assets_dir(assets_dir: str | Path | None) -> Path:
    if assets_dir is not None:
        return Path(assets_dir).expanduser().resolve()
    return (
        Path(__file__).resolve().parents[2]
        / "assets"
        / "kenney_nature-kit"
        / "Models"
        / "GLTF format"
    )


def _as_polydata(mesh: Any) -> pv.PolyData:
    if isinstance(mesh, pv.PolyData):
        return mesh
    if isinstance(mesh, pv.MultiBlock):
        return mesh.combine().extract_surface().triangulate()
    return mesh.extract_surface().triangulate()


def _iter_polydata_blocks(dataset: Any) -> list[pv.PolyData]:
    if isinstance(dataset, pv.MultiBlock):
        blocks: list[pv.PolyData] = []
        for block in dataset:
            if block is None:
                continue
            blocks.extend(_iter_polydata_blocks(block))
        return blocks
    return [_as_polydata(dataset)]


def _extract_base_color(mesh: pv.PolyData) -> tuple[float, float, float] | None:
    if "BaseColorMultiplier" not in mesh.field_data:
        return None
    rgba = np.asarray(mesh.field_data["BaseColorMultiplier"]).reshape(-1)
    if rgba.size < 3:
        return None
    return (float(np.clip(rgba[0], 0.0, 1.0)), float(np.clip(rgba[1], 0.0, 1.0)), float(np.clip(rgba[2], 0.0, 1.0)))


def _load_tree_meshes(assets_dir: Path) -> list[list[tuple[pv.PolyData, tuple[float, float, float] | None]]]:
    model_meshes: list[list[tuple[pv.PolyData, tuple[float, float, float] | None]]] = []
    for name in TREE_MODEL_NAMES:
        model_path = assets_dir / name
        parts = _iter_polydata_blocks(pv.read(model_path))
        if not parts:
            continue

        combined = parts[0].copy(deep=True)
        for part in parts[1:]:
            combined = combined.merge(part)

        # GLB trees are authored with Y-up; rotate to Z-up so trees stand vertically on each tile.
        x_span = combined.bounds[1] - combined.bounds[0]
        y_span = combined.bounds[3] - combined.bounds[2]
        z_span = combined.bounds[5] - combined.bounds[4]
        dominant_axis = int(np.argmax([x_span, y_span, z_span]))
        x_rot = 0.0
        y_rot = 0.0
        if dominant_axis == 0:
            y_rot = 90.0
        elif dominant_axis == 1:
            x_rot = 90.0

        rotated_parts: list[tuple[pv.PolyData, tuple[float, float, float] | None]] = []
        for part in parts:
            transformed = part.copy(deep=True)
            if x_rot:
                transformed.rotate_x(x_rot, inplace=True)
            if y_rot:
                transformed.rotate_y(y_rot, inplace=True)
            rotated_parts.append((transformed, _extract_base_color(part)))

        rotated_combined = rotated_parts[0][0].copy(deep=True)
        for part_mesh, _ in rotated_parts[1:]:
            rotated_combined = rotated_combined.merge(part_mesh)

        bounds = rotated_combined.bounds
        cx = 0.5 * (bounds[0] + bounds[1])
        cy = 0.5 * (bounds[2] + bounds[3])
        min_z = bounds[4]
        normalized_height = max(bounds[5] - bounds[4], 1e-6)
        scale = 0.85 / normalized_height

        normalized_parts: list[tuple[pv.PolyData, tuple[float, float, float] | None]] = []
        for part_mesh, part_color in rotated_parts:
            transformed = part_mesh.copy(deep=True)
            transformed.translate((-cx, -cy, -min_z), inplace=True)
            transformed.scale(scale, inplace=True)
            normalized_parts.append((transformed, part_color))

        model_meshes.append(normalized_parts)
    return model_meshes


def _load_dry_bush_meshes(assets_dir: Path) -> list[list[tuple[pv.PolyData, tuple[float, float, float] | None]]]:
    model_meshes: list[list[tuple[pv.PolyData, tuple[float, float, float] | None]]] = []
    for name in DRY_BUSH_MODEL_NAMES:
        model_path = assets_dir / name
        if not model_path.exists():
            continue

        parts = _iter_polydata_blocks(pv.read(model_path))
        if not parts:
            continue

        combined = parts[0].copy(deep=True)
        for part in parts[1:]:
            combined = combined.merge(part)

        bounds = combined.bounds
        cx = 0.5 * (bounds[0] + bounds[1])
        cy = 0.5 * (bounds[2] + bounds[3])
        min_z = bounds[4]
        normalized_height = max(bounds[5] - bounds[4], 1e-6)
        scale = 0.30 / normalized_height

        normalized_parts: list[tuple[pv.PolyData, tuple[float, float, float] | None]] = []
        for part in parts:
            transformed = part.copy(deep=True)
            transformed.translate((-cx, -cy, -min_z), inplace=True)
            transformed.scale(scale, inplace=True)
            normalized_parts.append((transformed, _extract_base_color(part)))

        model_meshes.append(normalized_parts)
    return model_meshes


def show_wildfire_result_3d(
    postprocess: dict[str, Any],
    *,
    title: str = "Wildfire Shrub Placement (3D)",
    assets_dir: str | Path | None = None,
    block: bool = True,
    screenshot_path: str | Path | None = None,
) -> pv.Plotter | None:
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
    plotter = pv.Plotter(window_size=[1400, 900], off_screen=bool(screenshot_path and not block))
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
    if not tree_meshes:
        raise ValueError(f"No GLB tree models found in: {assets_path}")
    dry_bush_meshes = _load_dry_bush_meshes(assets_path)

    seen: set[tuple[int, int]] = set()
    for idx, cell in enumerate(selected_cells):
        if not isinstance(cell, (list, tuple)) or len(cell) < 2:
            continue
        r = int(cell[0])
        c = int(cell[1])
        if (r, c) in seen or not (0 <= r < rows and 0 <= c < cols):
            continue
        seen.add((r, c))

        tree_parts = tree_meshes[idx % len(tree_meshes)]
        rotation = float((idx * 47) % 360)
        z_offset = 0.08 + 0.07 * float(np.clip(fuel_map[r, c], 0.0, 1.0))
        for base_part, part_color in tree_parts:
            tree = base_part.copy(deep=True)
            tree = tree.rotate_z(rotation, inplace=False)
            tree = tree.translate((float(c), float(rows - 1 - r), z_offset), inplace=False)

            add_kwargs: dict[str, Any] = {
                "smooth_shading": True,
                "ambient": 0.2,
                "diffuse": 0.75,
                "specular": 0.12,
            }
            if part_color is not None:
                add_kwargs["color"] = part_color
            plotter.add_mesh(tree, **add_kwargs)

    # Render unselected high-fuel cells as dry bush models to show remaining fire risk.
    if dry_bush_meshes:
        dry_color = (0.60, 0.43, 0.22)
        dry_cells = [
            (r, c)
            for r in range(rows)
            for c in range(cols)
            if float(fuel_map[r, c]) > 0.5 and (r, c) not in seen
        ]
        for idx, (r, c) in enumerate(dry_cells):
            bush_parts = dry_bush_meshes[idx % len(dry_bush_meshes)]
            rotation = float((idx * 29) % 360)
            z_offset = 0.03 + 0.07 * float(np.clip(fuel_map[r, c], 0.0, 1.0))
            for base_part, _part_color in bush_parts:
                bush = base_part.copy(deep=True)
                bush = bush.rotate_z(rotation, inplace=False)
                bush = bush.translate((float(c), float(rows - 1 - r), z_offset), inplace=False)
                plotter.add_mesh(
                    bush,
                    color=dry_color,
                    smooth_shading=True,
                    ambient=0.22,
                    diffuse=0.72,
                    specular=0.06,
                )

    # Add subtle grid accents so each shrub marker sits on a visibly distinct tile.
    for r in range(rows + 1):
        y = float(r - 0.5)
        plotter.add_lines(np.array([[-0.5, y, 0.001], [cols - 0.5, y, 0.001]]), color="#2a2f39", width=1)
    for c in range(cols + 1):
        x = float(c - 0.5)
        plotter.add_lines(np.array([[x, -0.5, 0.001], [x, rows - 0.5, 0.001]]), color="#2a2f39", width=1)

    plotter.add_title(title, font_size=14, color="white")
    plotter.add_text(
        "Forest-green risk tiles + tree markers (selected) + dry bush markers (unselected)",
        position="lower_left",
        font_size=10,
        color="white",
    )
    plotter.camera_position = [
        (float(cols) * 1.2, float(-rows) * 1.4, float(max(rows, cols)) * 1.5),
        (float(cols) * 0.5 - 0.5, float(rows) * 0.5 - 0.5, 0.0),
        (0.0, 0.0, 1.0),
    ]

    if screenshot_path:
        path = Path(screenshot_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        plotter.show(auto_close=False)
        plotter.screenshot(str(path))
        plotter.close()
        return None

    if block:
        plotter.show(auto_close=False)
        return None

    plotter.show(interactive=True, auto_close=False, interactive_update=True)
    return plotter



