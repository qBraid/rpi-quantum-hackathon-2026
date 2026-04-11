from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.algorithms.qaoa import QAOAProblem, approximation_ratio, brute_force_best, build_qaoa_circuit, qaoa_level1
from app.models import OptimizationRun, Scenario
from app.services.wildfire_model import (
    CELL_LIBRARY,
    adjacency_metrics,
    build_environment,
    default_environment,
    normalize_grid,
    orthogonal_neighbors,
    run_stochastic_forecast,
)

PLANNING_MODE = "planning"
CHALLENGE_MODE = "challenge"
CHALLENGE_BUDGET = 10
DEFAULT_ENVIRONMENT = {
    "dryness": 0.74,
    "spread_sensitivity": 0.64,
    "wind_speed": 0.58,
    "wind_direction": "NE",
    "slope_influence": 0.42,
    "spotting_likelihood": 0.08,
    "suppression_effectiveness": 0.2,
    "ensemble_runs": 24,
    "slope_layer": [[0.0 for _ in range(10)] for _ in range(10)],
}
PLAYBACK_STEPS = 6
PLAYBACK_RUNS = 16


def _apply_placements(grid: list[list[str]], placements: list[dict]) -> list[list[str]]:
    updated = [row[:] for row in normalize_grid(grid)]
    for placement in placements:
        updated[placement["row"]][placement["col"]] = "intervention"
    return updated


def _evaluate_grid(grid: list[list[str]], environment: dict, seed: int, runs: int) -> dict:
    forecast = run_stochastic_forecast(grid, environment, steps=6, seed=seed, runs=runs)
    metrics = adjacency_metrics(grid)
    return {
        "forecast": forecast,
        "metrics": {
            **metrics,
            "mean_final_burned_area": forecast["summary"]["mean_final_burned_area"],
            "p90_final_burned_area": forecast["summary"]["p90_final_burned_area"],
            "peak_burn_probability": forecast["summary"]["peak_burn_probability"],
        },
    }


def _planning_objective_score(evaluation: dict) -> float:
    metrics = evaluation["metrics"]
    return round(
        float(
            0.9 * metrics["adjacency_links"]
            + 0.75 * metrics["largest_component"]
            + 1.85 * metrics["mean_final_burned_area"]
            + 1.25 * metrics["p90_final_burned_area"]
            + 16.0 * metrics["peak_burn_probability"]
        ),
        4,
    )


def _candidate_base_rows(grid: list[list[str]], burn_probability_lookup: dict[str, float], ignition_time_lookup: dict[str, float | None]) -> list[dict]:
    normalized = normalize_grid(grid)
    rows: list[dict] = []
    for row, line in enumerate(normalized):
        for col, state in enumerate(line):
            semantics = CELL_LIBRARY[state]
            if not semantics.burnable or state in {"ignition", "burned"}:
                continue
            key = f"{row}-{col}"
            corridor_score = sum(
                burn_probability_lookup.get(f"{nr}-{nc}", 0.0)
                for nr, nc in orthogonal_neighbors(row, col, len(normalized))
            )
            rows.append(
                {
                    "row": row,
                    "col": col,
                    "state": state,
                    "burn_probability": round(float(burn_probability_lookup.get(key, 0.0)), 4),
                    "expected_ignition_time": ignition_time_lookup.get(key),
                    "corridor_pressure": round(float(corridor_score), 4),
                    "component_contains_ignition": bool(burn_probability_lookup.get(key, 0.0) >= 0.45),
                    "treated": state in {"protected", "intervention"},
                }
            )
    return rows


def _candidate_impact(grid: list[list[str]], candidate: dict) -> dict:
    neighbor_pressure = sum(
        1
        for nr, nc in orthogonal_neighbors(candidate["row"], candidate["col"], len(grid))
        if CELL_LIBRARY[grid[nr][nc]].burnable
    )
    return {
        **candidate,
        "expected_burned_area_reduction": round(candidate["burn_probability"] * (1.1 + 0.15 * neighbor_pressure), 4),
        "burn_probability_reduction": round(candidate["burn_probability"] * (0.3 + 0.08 * neighbor_pressure), 4),
        "corridor_disruption": round(candidate["corridor_pressure"], 4),
        "connectivity_reduction": neighbor_pressure,
        "blocked_links": neighbor_pressure,
        "ignition_delay": round((candidate["expected_ignition_time"] or 0.0) * 0.1, 4),
        "score": round(
            candidate["burn_probability"] * 1.7
            + candidate["corridor_pressure"] * 0.55
            + candidate["burn_probability"] * (1.2 + 0.18 * neighbor_pressure)
            + neighbor_pressure * 0.35,
            4,
        ),
    }


def candidate_rows(grid: list[list[str]], environment: dict | None = None) -> list[dict]:
    working_environment = build_environment(DEFAULT_ENVIRONMENT, **(environment or {}))
    baseline = _evaluate_grid(grid, working_environment, seed=17, runs=10)
    base_rows = _candidate_base_rows(
        grid,
        baseline["forecast"]["burn_probability_lookup"],
        baseline["forecast"]["expected_ignition_time_lookup"],
    )
    scored = [_candidate_impact(normalize_grid(grid), candidate) for candidate in base_rows]
    return sorted(scored, key=lambda item: (item["score"], item["burn_probability"]), reverse=True)


def _greedy_classical_plan(grid: list[list[str]], enforced_budget: int, environment: dict) -> dict:
    working_grid = normalize_grid(grid)
    baseline = _evaluate_grid(working_grid, environment, seed=41, runs=18)
    placements: list[dict] = []
    for _ in range(enforced_budget):
        ranked = [item for item in candidate_rows(working_grid, environment) if (item["row"], item["col"]) not in {(p["row"], p["col"]) for p in placements}]
        if not ranked:
            break
        choice = ranked[0]
        placements.append(choice)
        working_grid[choice["row"]][choice["col"]] = "intervention"
    after = _evaluate_grid(working_grid, environment, seed=59, runs=18)
    return {
        "placements": placements,
        "metrics_before": baseline["metrics"],
        "metrics_after": after["metrics"],
        "objective_before": _planning_objective_score(baseline),
        "objective_after": _planning_objective_score(after),
        "forecast_before": baseline["forecast"]["summary"],
        "forecast_after": after["forecast"]["summary"],
        "forecast_before_detail": baseline["forecast"],
        "forecast_after_detail": after["forecast"],
    }


def _tactical_candidate_impact(grid: list[list[str]], candidate: dict) -> dict:
    early_front_bonus = 0.0
    if candidate["expected_ignition_time"] is not None:
        early_front_bonus = max(0.0, 1.2 - float(candidate["expected_ignition_time"]) / 4.0)
    neighbor_pressure = sum(
        1
        for nr, nc in orthogonal_neighbors(candidate["row"], candidate["col"], len(grid))
        if CELL_LIBRARY[grid[nr][nc]].burnable
    )
    return {
        **candidate,
        "expected_burned_area_reduction": round(candidate["burn_probability"] * (0.95 + 0.12 * neighbor_pressure), 4),
        "burn_probability_reduction": round(candidate["burn_probability"] * (0.28 + 0.08 * neighbor_pressure), 4),
        "corridor_disruption": round(candidate["corridor_pressure"] * 0.7, 4),
        "connectivity_reduction": neighbor_pressure,
        "blocked_links": neighbor_pressure,
        "ignition_delay": round(0.35 + early_front_bonus * 0.7, 4),
        "score": round(
            candidate["burn_probability"] * 1.45
            + early_front_bonus * 1.8
            + candidate["corridor_pressure"] * 0.35
            + neighbor_pressure * 0.3,
            4,
        ),
    }


def _greedy_tactical_plan(grid: list[list[str]], enforced_budget: int, environment: dict) -> dict:
    working_grid = normalize_grid(grid)
    baseline = _evaluate_grid(working_grid, environment, seed=43, runs=18)
    base_rows = _candidate_base_rows(
        working_grid,
        baseline["forecast"]["burn_probability_lookup"],
        baseline["forecast"]["expected_ignition_time_lookup"],
    )
    placements: list[dict] = []
    for _ in range(enforced_budget):
        ranked = [
            _tactical_candidate_impact(working_grid, item)
            for item in base_rows
            if (item["row"], item["col"]) not in {(p["row"], p["col"]) for p in placements}
            and working_grid[item["row"]][item["col"]] not in {"intervention", "water", "road_or_firebreak"}
        ]
        ranked.sort(key=lambda item: (item["score"], item["burn_probability"]), reverse=True)
        if not ranked:
            break
        choice = ranked[0]
        placements.append(choice)
        working_grid[choice["row"]][choice["col"]] = "intervention"
    after = _evaluate_grid(working_grid, environment, seed=61, runs=18)
    return {
        "placements": placements,
        "metrics_before": baseline["metrics"],
        "metrics_after": after["metrics"],
        "objective_before": _planning_objective_score(baseline),
        "objective_after": _planning_objective_score(after),
        "forecast_before": baseline["forecast"]["summary"],
        "forecast_after": after["forecast"]["summary"],
        "forecast_before_detail": baseline["forecast"],
        "forecast_after_detail": after["forecast"],
    }


def _reduced_quantum_study(grid: list[list[str]], reduced_count: int, enforced_budget: int, environment: dict, mode: str) -> dict:
    shortlist = candidate_rows(grid, environment)[:reduced_count]
    reduced = shortlist[: min(8, len(shortlist))]
    weights = [round(float(item["score"]), 4) for item in reduced]
    penalties: dict[tuple[int, int], float] = {}
    for idx, item in enumerate(reduced):
        for jdx in range(idx + 1, len(reduced)):
            other = reduced[jdx]
            if abs(item["row"] - other["row"]) + abs(item["col"] - other["col"]) <= 1:
                penalties[(idx, jdx)] = 0.3
    problem = QAOAProblem(weights=weights, pair_penalties=penalties, budget=min(enforced_budget, len(reduced)))
    qaoa = qaoa_level1(problem)
    exact_bits, exact_cost = brute_force_best(problem)
    selected = [reduced[idx] for idx, bit in enumerate(qaoa["best_bitstring"]) if bit == 1]
    circuit = build_qaoa_circuit(problem, qaoa["gamma"], qaoa["beta"])
    note = (
        "Full-grid planning stays classical. The quantum study benchmarks a reduced candidate graph derived from the same burn-probability and corridor model used in forecast and risk."
        if mode == PLANNING_MODE
        else "The full 10x10 challenge graph is evaluated classically. The quantum study uses a reduced shortlist derived from that same adjacency graph for tractable QAOA analysis."
    )
    return {
        "scope": {
            "type": "reduced_critical_subgraph",
            "candidate_count": len(reduced),
            "shortlist_count": len(shortlist),
            "budget": min(enforced_budget, len(reduced)),
            "note": note,
        },
        "placements": selected,
        "candidate_shortlist": shortlist,
        "qaoa": qaoa,
        "approximation_ratio": approximation_ratio(problem, qaoa["expected_cost"]),
        "exact_baseline": {"best_bitstring": list(exact_bits), "best_cost": round(float(exact_cost), 4)},
        "circuit": {"num_qubits": circuit.num_qubits, "depth": circuit.depth(), "gate_counts": dict(circuit.count_ops())},
    }


def _placement_reason(placement: dict, shared: bool, mode: str) -> str:
    reasons = []
    if mode == CHALLENGE_MODE:
        if placement.get("challenge_disrupted_edges", 0) > 0:
            reasons.append("removes adjacency paths from the challenge graph")
        if placement.get("challenge_degree", 0) >= 2:
            reasons.append("covers a dense dry-brush cluster")
        if shared:
            reasons.append("appears in both the classical challenge plan and reduced quantum shortlist")
    else:
        if placement["connectivity_reduction"] > 0:
            reasons.append("blocks a major fuel corridor")
        if placement["burn_probability"] >= 0.55:
            reasons.append("protects a high-probability spread pathway")
        if placement["expected_burned_area_reduction"] > 0.5:
            reasons.append("reduces expected burned area")
        if placement["ignition_delay"] > 0:
            reasons.append("delays the likely ignition front")
        if shared:
            reasons.append("chosen by both classical planning and the reduced quantum study")
    return ", ".join(reasons[:3]).capitalize() + "." if reasons else "Adds modest resilience value under the active wildfire objective."


def _plan_explanation(plan_type: str, status: str, metrics_before: dict, metrics_after: dict) -> str:
    mean_delta = round(metrics_before.get("mean_final_burned_area", 0.0) - metrics_after.get("mean_final_burned_area", 0.0), 3)
    p90_delta = round(metrics_before.get("p90_final_burned_area", 0.0) - metrics_after.get("p90_final_burned_area", 0.0), 3)
    link_delta = round(metrics_before.get("adjacency_links", 0.0) - metrics_after.get("adjacency_links", 0.0), 3)
    if plan_type == "containment":
        base = "This containment-oriented plan focuses on slowing the near-term ignition front around the highest-pressure cells."
    elif plan_type == "corridor":
        base = "This corridor-cut plan focuses on breaking the strongest spread pathways across connected fuel patches."
    elif plan_type == "challenge":
        base = "This challenge-facing plan removes dry-brush adjacency links on the posted 10x10 graph with strict K=10 placement."
    else:
        base = "This plan is derived from the reduced quantum shortlist but evaluated classically on the full grid."

    outcome = (
        f" It changes mean burned area by {mean_delta}, P90 burned area by {p90_delta}, and breaks {link_delta} adjacency links."
        if "mean_final_burned_area" in metrics_before
        else ""
    )
    if status == "tradeoff":
        outcome += " It improves structural disruption but should be treated as a tradeoff rather than the default recommendation."
    elif status == "no_clear_gain":
        outcome += " No strong intervention gain over baseline was found under the current forecast settings."
    return base + outcome


def _quantum_informed_plan(grid: list[list[str]], classical: dict, quantum: dict, environment: dict, enforced_budget: int) -> dict:
    classical_map = {(item["row"], item["col"]): item for item in classical["placements"]}
    quantum_keys = {(item["row"], item["col"]) for item in quantum["placements"]}
    placements: list[dict] = []
    used: set[tuple[int, int]] = set()
    for key in list(classical_map.keys() & quantum_keys):
        choice = {**classical_map[key], "selected_by_classical": True, "selected_by_quantum": True}
        choice["reason"] = _placement_reason(choice, True, PLANNING_MODE)
        placements.append(choice)
        used.add(key)
    for item in quantum["placements"]:
        key = (item["row"], item["col"])
        if key in used or len(placements) >= enforced_budget:
            continue
        enriched = {**classical_map.get(key, item), "selected_by_classical": key in classical_map, "selected_by_quantum": True}
        enriched["reason"] = _placement_reason(enriched, key in classical_map, PLANNING_MODE)
        placements.append(enriched)
        used.add(key)
    for item in classical["placements"]:
        key = (item["row"], item["col"])
        if key in used or len(placements) >= enforced_budget:
            continue
        enriched = {**item, "selected_by_classical": True, "selected_by_quantum": False}
        enriched["reason"] = _placement_reason(enriched, False, PLANNING_MODE)
        placements.append(enriched)
        used.add(key)
    updated = _apply_placements(grid, placements)
    after = _evaluate_grid(updated, environment, seed=83, runs=18)
    baseline_metrics = classical["metrics_before"]
    return {
        "placements": placements,
        "metrics_before": baseline_metrics,
        "metrics_after": after["metrics"],
        "objective_before": classical["objective_before"],
        "objective_after": _planning_objective_score(after),
        "forecast_after": after["forecast"]["summary"],
        "forecast_before": classical["forecast_before"],
        "forecast_before_detail": classical["forecast_before_detail"],
        "forecast_after_detail": after["forecast"],
        "agreement_count": len(classical_map.keys() & quantum_keys),
    }


def _plan_acceptance(baseline_metrics: dict, candidate: dict) -> tuple[str, str]:
    before_mean = baseline_metrics["mean_final_burned_area"]
    after_mean = candidate["metrics_after"]["mean_final_burned_area"]
    before_p90 = baseline_metrics["p90_final_burned_area"]
    after_p90 = candidate["metrics_after"]["p90_final_burned_area"]
    before_links = baseline_metrics["adjacency_links"]
    after_links = candidate["metrics_after"]["adjacency_links"]
    before_peak = baseline_metrics["peak_burn_probability"]
    after_peak = candidate["metrics_after"]["peak_burn_probability"]

    mean_delta = round(after_mean - before_mean, 4)
    p90_delta = round(after_p90 - before_p90, 4)
    link_delta = round(before_links - after_links, 4)
    peak_delta = round(before_peak - after_peak, 4)

    worsens_burn = mean_delta > 0.1 or p90_delta > 0.2
    meaningful_improvement = mean_delta <= -0.2 or p90_delta <= -0.2 or link_delta >= 1 or peak_delta >= 0.01

    if not worsens_burn and meaningful_improvement:
        return (
            "recommended",
            "Accepted because it preserves or improves burned-area outcomes while improving at least one major resilience objective.",
        )
    if meaningful_improvement:
        return (
            "tradeoff",
            "Improves corridor or graph structure, but worsens burned-area outcomes beyond the safe recommendation tolerance.",
        )
    return (
        "no_clear_gain",
        "No strong intervention improvement was found under the current planning settings, so baseline is retained as the safe default.",
    )


def _selection_score(plan: dict, baseline_metrics: dict) -> tuple[float, float, float]:
    return (
        plan["metrics_after"]["mean_final_burned_area"] - baseline_metrics["mean_final_burned_area"],
        plan["metrics_after"]["p90_final_burned_area"] - baseline_metrics["p90_final_burned_area"],
        plan["objective_after"],
    )


def _baseline_hold(classical: dict) -> dict:
    return {
        "placements": [],
        "metrics_before": classical["metrics_before"],
        "metrics_after": classical["metrics_before"],
        "objective_before": classical["objective_before"],
        "objective_after": classical["objective_before"],
        "forecast_after": classical["forecast_before"],
        "agreement_count": 0,
    }


def _recommend_planning_plan(classical: dict, quantum_informed: dict) -> tuple[str, str, str, dict, dict | None]:
    baseline_metrics = classical["metrics_before"]
    candidates = {
        "classical_full_plan": classical,
        "quantum_informed_plan": quantum_informed,
    }
    assessments = {name: _plan_acceptance(baseline_metrics, plan) for name, plan in candidates.items()}
    safe = [name for name, (status, _) in assessments.items() if status == "recommended"]
    if safe:
        best_name = min(safe, key=lambda name: _selection_score(candidates[name], baseline_metrics))
        return best_name, "recommended", assessments[best_name][1], candidates[best_name], None

    tradeoffs = [name for name, (status, _) in assessments.items() if status == "tradeoff"]
    if tradeoffs:
        best_tradeoff = min(tradeoffs, key=lambda name: candidates[name]["objective_after"])
        return "baseline_hold", "tradeoff", assessments[best_tradeoff][1], _baseline_hold(classical), candidates[best_tradeoff]

    return "baseline_hold", "no_clear_gain", assessments["classical_full_plan"][1], _baseline_hold(classical), None


def _recommend_multi_plan(candidates: dict[str, dict]) -> tuple[str, str, str, dict, dict | None]:
    first = next(iter(candidates.values()))
    baseline_metrics = first["metrics_before"]
    assessments = {name: _plan_acceptance(baseline_metrics, plan) for name, plan in candidates.items()}
    safe = [name for name, (status, _) in assessments.items() if status == "recommended"]
    if safe:
        best_name = min(safe, key=lambda name: _selection_score(candidates[name], baseline_metrics))
        return best_name, "recommended", assessments[best_name][1], candidates[best_name], None
    tradeoffs = [name for name, (status, _) in assessments.items() if status == "tradeoff"]
    if tradeoffs:
        best_tradeoff = min(tradeoffs, key=lambda name: candidates[name]["objective_after"])
        return "baseline_hold", "tradeoff", assessments[best_tradeoff][1], _baseline_hold(first), candidates[best_tradeoff]
    best_no_gain = min(candidates.keys(), key=lambda name: candidates[name]["objective_after"])
    return "baseline_hold", "no_clear_gain", assessments[best_no_gain][1], _baseline_hold(first), None


def _challenge_graph(grid: list[list[str]]) -> tuple[list[dict], list[tuple[int, int]]]:
    normalized = normalize_grid(grid)
    nodes: list[dict] = []
    flammable_positions: set[tuple[int, int]] = set()
    for row, line in enumerate(normalized):
        for col, state in enumerate(line):
            semantics = CELL_LIBRARY[state]
            if semantics.burnable and state not in {"protected", "intervention", "burned"}:
                nodes.append({"row": row, "col": col, "state": state, "key": (row, col)})
            if state in {"dry_brush", "ignition"}:
                flammable_positions.add((row, col))
    index_lookup = {node["key"]: idx for idx, node in enumerate(nodes)}
    edges: list[tuple[int, int]] = []
    for row, col in sorted(flammable_positions):
        for nr, nc in orthogonal_neighbors(row, col, len(normalized)):
            if (nr, nc) in flammable_positions and index_lookup[(row, col)] < index_lookup[(nr, nc)]:
                edges.append((index_lookup[(row, col)], index_lookup[(nr, nc)]))
    return nodes, edges


def _challenge_cost(nodes: list[dict], edges: list[tuple[int, int]], selected: set[tuple[int, int]], budget: int) -> dict:
    surviving_edges = sum(1 for left, right in edges if nodes[left]["key"] not in selected and nodes[right]["key"] not in selected)
    penalty = (len(selected) - budget) ** 2
    return {
        "cost": round(float(surviving_edges + penalty), 4),
        "surviving_edges": surviving_edges,
        "penalty": penalty,
    }


def _challenge_candidate_rows(grid: list[list[str]]) -> list[dict]:
    nodes, edges = _challenge_graph(grid)
    degree = {node["key"]: 0 for node in nodes}
    for left, right in edges:
        degree[nodes[left]["key"]] += 1
        degree[nodes[right]["key"]] += 1
    ranked = []
    for node in nodes:
        ranked.append(
            {
                "row": node["row"],
                "col": node["col"],
                "state": node["state"],
                "challenge_degree": degree[node["key"]],
                "challenge_disrupted_edges": degree[node["key"]],
                "score": float(degree[node["key"]]),
            }
        )
    return sorted(ranked, key=lambda item: (item["challenge_degree"], item["state"] in {"dry_brush", "ignition"}), reverse=True)


def _difference_summary(baseline_forecast: dict, plan_forecast: dict) -> dict:
    baseline_prob = baseline_forecast["burn_probability_lookup"]
    plan_prob = plan_forecast["burn_probability_lookup"]
    baseline_time = baseline_forecast["expected_ignition_time_lookup"]
    plan_time = plan_forecast["expected_ignition_time_lookup"]

    protected_cells = sum(
        1
        for key, baseline_value in baseline_prob.items()
        if baseline_value >= 0.45 and plan_prob.get(key, baseline_value) < 0.45
    )
    delayed_ignition = sum(
        1
        for key, baseline_value in baseline_time.items()
        if baseline_value is not None and plan_time.get(key) is not None and float(plan_time[key]) - float(baseline_value) >= 1.0
    )
    reduced_corridors = max(
        0,
        len(baseline_forecast["summary"].get("likely_spread_corridors", [])) - len(plan_forecast["summary"].get("likely_spread_corridors", [])),
    )
    mean_delta = round(
        baseline_forecast["summary"]["mean_final_burned_area"] - plan_forecast["summary"]["mean_final_burned_area"],
        4,
    )
    p90_delta = round(
        baseline_forecast["summary"]["p90_final_burned_area"] - plan_forecast["summary"]["p90_final_burned_area"],
        4,
    )
    material = mean_delta >= 0.2 or p90_delta >= 0.2 or protected_cells >= 2
    return {
        "protected_cells_by_threshold": protected_cells,
        "delayed_ignition_cells": delayed_ignition,
        "reduced_spread_corridor_cells": reduced_corridors,
        "mean_burned_area_difference": mean_delta,
        "p90_burned_area_difference": p90_delta,
        "material_outperformance": material,
    }


def _build_playback_comparison(baseline_forecast: dict, plan_forecast: dict) -> dict:
    baseline_snapshots = baseline_forecast.get("representative_snapshots", [])
    plan_snapshots = plan_forecast.get("representative_snapshots", [])
    step_count = min(len(baseline_snapshots), len(plan_snapshots))
    synchronized = []
    for step in range(step_count):
        baseline_grid = baseline_snapshots[step]["grid"]
        plan_grid = plan_snapshots[step]["grid"]
        changed = 0
        protected = 0
        for row in range(len(baseline_grid)):
            for col in range(len(baseline_grid[row])):
                if baseline_grid[row][col] != plan_grid[row][col]:
                    changed += 1
                if baseline_grid[row][col] in {"ignition", "burned"} and plan_grid[row][col] not in {"ignition", "burned"}:
                    protected += 1
        synchronized.append(
            {
                "step": step,
                "baseline": baseline_snapshots[step],
                "with_plan": plan_snapshots[step],
                "difference": {
                    "changed_cells": changed,
                    "protected_cells": protected,
                },
            }
        )
    return {
        "steps": synchronized,
        "step_count": step_count,
        "difference_summary": _difference_summary(baseline_forecast, plan_forecast),
    }


def _challenge_classical_plan(grid: list[list[str]], enforced_budget: int) -> dict:
    nodes, edges = _challenge_graph(grid)
    degree = {node["key"]: 0 for node in nodes}
    for left, right in edges:
        degree[nodes[left]["key"]] += 1
        degree[nodes[right]["key"]] += 1

    selected: set[tuple[int, int]] = set()
    placements: list[dict] = []
    current = _challenge_cost(nodes, edges, selected, enforced_budget)
    for _ in range(min(enforced_budget, len(nodes))):
        best_choice = None
        best_cost = None
        for node in nodes:
            key = node["key"]
            if key in selected:
                continue
            trial_selected = selected | {key}
            trial = _challenge_cost(nodes, edges, trial_selected, enforced_budget)
            if best_choice is None or trial["cost"] < best_cost["cost"] or (
                trial["cost"] == best_cost["cost"] and degree[key] > degree[best_choice["key"]]
            ):
                best_choice = node
                best_cost = trial
        if best_choice is None:
            break
        key = best_choice["key"]
        selected.add(key)
        placements.append(
            {
                "row": best_choice["row"],
                "col": best_choice["col"],
                "state": best_choice["state"],
                "challenge_degree": degree[key],
                "challenge_disrupted_edges": degree[key],
                "selected_by_classical": True,
                "selected_by_quantum": False,
            }
        )
        current = best_cost

    before = _challenge_cost(nodes, edges, set(), enforced_budget)
    after = _challenge_cost(nodes, edges, selected, enforced_budget)
    return {
        "placements": placements,
        "metrics_before": {
            "challenge_cost": before["cost"],
            "surviving_edges": before["surviving_edges"],
            "budget_penalty": before["penalty"],
            "adjacency_links": before["surviving_edges"],
        },
        "metrics_after": {
            "challenge_cost": after["cost"],
            "surviving_edges": after["surviving_edges"],
            "budget_penalty": after["penalty"],
            "adjacency_links": after["surviving_edges"],
        },
        "objective_before": before["cost"],
        "objective_after": after["cost"],
        "challenge_graph": {"node_count": len(nodes), "edge_count": len(edges)},
    }


def _challenge_quantum_study(grid: list[list[str]], reduced_count: int, enforced_budget: int) -> dict:
    shortlist = _challenge_candidate_rows(grid)[:reduced_count]
    reduced = shortlist[: min(8, len(shortlist))]
    index = {(item["row"], item["col"]): idx for idx, item in enumerate(reduced)}
    weights = [max(1.0, float(item["challenge_degree"])) for item in reduced]
    penalties: dict[tuple[int, int], float] = {}
    normalized = normalize_grid(grid)
    for item in reduced:
        for nr, nc in orthogonal_neighbors(item["row"], item["col"], len(normalized)):
            other_idx = index.get((nr, nc))
            if other_idx is not None and index[(item["row"], item["col"])] < other_idx and normalized[item["row"]][item["col"]] in {"dry_brush", "ignition"} and normalized[nr][nc] in {"dry_brush", "ignition"}:
                penalties[(index[(item["row"], item["col"])], other_idx)] = 0.4
    problem = QAOAProblem(weights=weights, pair_penalties=penalties, budget=min(enforced_budget, len(reduced)))
    qaoa = qaoa_level1(problem)
    exact_bits, exact_cost = brute_force_best(problem)
    selected = [reduced[idx] for idx, bit in enumerate(qaoa["best_bitstring"]) if bit == 1]
    circuit = build_qaoa_circuit(problem, qaoa["gamma"], qaoa["beta"])
    return {
        "scope": {
            "type": "reduced_challenge_subgraph",
            "candidate_count": len(reduced),
            "shortlist_count": len(shortlist),
            "budget": min(enforced_budget, len(reduced)),
            "note": "The reduced QAOA study is carved directly out of the same 10x10 challenge graph. It is a tractable benchmarked subproblem, not a full 100-node hardware solve.",
        },
        "placements": selected,
        "candidate_shortlist": shortlist,
        "qaoa": qaoa,
        "approximation_ratio": approximation_ratio(problem, qaoa["expected_cost"]),
        "exact_baseline": {"best_bitstring": list(exact_bits), "best_cost": round(float(exact_cost), 4)},
        "circuit": {"num_qubits": circuit.num_qubits, "depth": circuit.depth(), "gate_counts": dict(circuit.count_ops())},
    }


def _create_planning_run(db: Session, scenario: Scenario, payload: dict, enforced_budget: int, environment: dict) -> OptimizationRun:
    classical = _greedy_classical_plan(scenario.grid, enforced_budget, environment)
    classical["plan_type"] = "corridor"
    classical["plan_label"] = "Challenge corridor plan"
    quantum = _reduced_quantum_study(scenario.grid, payload["reduced_candidate_count"], enforced_budget, environment, PLANNING_MODE)
    for placement in classical["placements"]:
        placement["selected_by_classical"] = True
        placement["selected_by_quantum"] = (placement["row"], placement["col"]) in {(p["row"], p["col"]) for p in quantum["placements"]}
        placement["reason"] = _placement_reason(placement, placement["selected_by_quantum"], PLANNING_MODE)
    quantum_informed = _quantum_informed_plan(scenario.grid, classical, quantum, environment, enforced_budget)
    quantum_informed["plan_type"] = "quantum_informed"
    quantum_informed["plan_label"] = "Quantum-informed corridor plan"
    for placement in quantum_informed["placements"]:
        if "reason" not in placement:
            placement["reason"] = _placement_reason(placement, placement.get("selected_by_quantum", False), PLANNING_MODE)
    tactical = _greedy_tactical_plan(scenario.grid, enforced_budget, environment)
    tactical["plan_type"] = "containment"
    tactical["plan_label"] = "Containment plan"
    quantum_informed["explanation"] = _plan_explanation("quantum_informed", "recommended", quantum_informed["metrics_before"], quantum_informed["metrics_after"])
    classical["explanation"] = _plan_explanation("corridor", "recommended", classical["metrics_before"], classical["metrics_after"])
    for placement in tactical["placements"]:
        placement["selected_by_classical"] = False
        placement["selected_by_quantum"] = (placement["row"], placement["col"]) in {(p["row"], p["col"]) for p in quantum["placements"]}
        placement["reason"] = _placement_reason(placement, placement["selected_by_quantum"], PLANNING_MODE)
    tactical["explanation"] = _plan_explanation("containment", "recommended", tactical["metrics_before"], tactical["metrics_after"])

    recommended_mode, recommendation_status, recommendation_reason, recommended, tradeoff_candidate = _recommend_multi_plan(
        {
            "corridor_plan": classical,
            "containment_plan": tactical,
            "quantum_informed_plan": quantum_informed,
        }
    )
    if recommended is classical:
        selected_plan_type = "corridor"
    elif recommended is tactical:
        selected_plan_type = "containment"
    elif recommended is quantum_informed:
        selected_plan_type = "quantum_informed"
    else:
        selected_plan_type = "baseline"
    if recommended_mode == "baseline_hold" and tradeoff_candidate is not None:
        recommended["plan_type"] = "baseline"
        recommended["plan_label"] = "Baseline hold"
        recommended["explanation"] = _plan_explanation(tradeoff_candidate.get("plan_type", "corridor"), recommendation_status, tradeoff_candidate["metrics_before"], tradeoff_candidate["metrics_after"])
    else:
        recommended["explanation"] = _plan_explanation(selected_plan_type, recommendation_status, recommended["metrics_before"], recommended["metrics_after"])

    baseline_metrics = classical["metrics_before"]
    recommended_metrics = recommended["metrics_after"]
    plan_comparisons = {
        "corridor": _build_playback_comparison(classical["forecast_before_detail"], classical["forecast_after_detail"]),
        "containment": _build_playback_comparison(tactical["forecast_before_detail"], tactical["forecast_after_detail"]),
        "quantum_informed": _build_playback_comparison(quantum_informed["forecast_before_detail"], quantum_informed["forecast_after_detail"]),
    }
    comparison = plan_comparisons.get(selected_plan_type, plan_comparisons["corridor"])
    results = {
        "mode": PLANNING_MODE,
        "objective": {
            "name": "planning_grade_resilience_gain",
            "description": "Combine corridor disruption with forecast-aware reduction in mean and P90 burned area under the shared wildfire ensemble model.",
            "budget_enforced_k": enforced_budget,
            "environment": {key: value for key, value in environment.items() if key != "slope_layer"},
        },
        "baseline": {"metrics": baseline_metrics, "forecast": classical["forecast_before"], "objective_score": classical["objective_before"]},
        "classical": classical,
        "corridor_plan": classical,
        "containment_plan": tactical,
        "quantum": quantum,
        "quantum_informed": quantum_informed,
        "recommended_plan": recommended,
        "tradeoff_candidate": tradeoff_candidate,
        "comparison_playback": comparison,
        "plan_comparisons": plan_comparisons,
    }
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": PLANNING_MODE,
        "recommended_mode": recommended_mode,
        "recommended_plan_type": selected_plan_type,
        "recommendation_status": recommendation_status,
        "recommendation_reason": recommendation_reason,
        "budget_requested_k": payload["intervention_budget_k"],
        "budget_enforced_k": enforced_budget,
        "before_mean_burned_area": baseline_metrics["mean_final_burned_area"],
        "after_mean_burned_area": recommended_metrics["mean_final_burned_area"],
        "before_p90_burned_area": baseline_metrics["p90_final_burned_area"],
        "after_p90_burned_area": recommended_metrics["p90_final_burned_area"],
        "expected_burned_area_reduction": round(baseline_metrics["mean_final_burned_area"] - recommended_metrics["mean_final_burned_area"], 4),
        "corridor_disruption": round(baseline_metrics["adjacency_links"] - recommended_metrics["adjacency_links"], 4),
        "link_reduction": round(baseline_metrics["adjacency_links"] - recommended_metrics["adjacency_links"], 4),
        "connectivity_reduction": round(baseline_metrics["adjacency_links"] - recommended_metrics["adjacency_links"], 4),
        "burn_probability_reduction": round(baseline_metrics["peak_burn_probability"] - recommended_metrics["peak_burn_probability"], 4),
        "high_risk_region_protection": sum(1 for item in recommended["placements"] if item.get("burn_probability", 0.0) >= 0.45),
        "ignition_time_delay_note": "Expected ignition-time delay is approximated through the ensemble impact score rather than a deterministic front.",
        "classical_plan_score": classical["objective_after"],
        "quantum_informed_plan_score": quantum_informed["objective_after"],
        "agreement_between_classical_and_quantum": quantum_informed["agreement_count"],
        "full_scale_scope": "Planning mode keeps full 10x10 intervention search classical and forecast-aware so the recommendation is evaluated against burned-area outcomes.",
        "reduced_quantum_scope": quantum["scope"],
        "planning_grade_note": "This is comparative pre-season planning support. It is not a live fire operations optimizer.",
        "broken_adjacency_links": baseline_metrics["adjacency_links"] - recommended_metrics["adjacency_links"],
        "spread_corridor_disruption": round(baseline_metrics["adjacency_links"] - recommended_metrics["adjacency_links"], 4),
        "coverage_high_risk_cells": sum(1 for item in recommended["placements"] if item.get("burn_probability", 0.0) >= 0.45),
        "plan_explanation": recommended.get("explanation", ""),
        "difference_summary": comparison["difference_summary"],
    }
    run = OptimizationRun(
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        request_json={**payload, "mode": PLANNING_MODE, "intervention_budget_k": enforced_budget},
        results_json=results,
        summary_json=summary,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _create_challenge_run(db: Session, scenario: Scenario, payload: dict, enforced_budget: int) -> OptimizationRun:
    classical = _challenge_classical_plan(scenario.grid, enforced_budget)
    classical["plan_type"] = "challenge"
    classical["plan_label"] = "Challenge corridor plan"
    quantum = _challenge_quantum_study(scenario.grid, payload["reduced_candidate_count"], enforced_budget)
    quantum_keys = {(item["row"], item["col"]) for item in quantum["placements"]}
    for placement in classical["placements"]:
        placement["selected_by_quantum"] = (placement["row"], placement["col"]) in quantum_keys
        placement["reason"] = _placement_reason(placement, placement["selected_by_quantum"], CHALLENGE_MODE)
    environment = build_environment(default_environment(scenario))
    baseline_forecast = run_stochastic_forecast(scenario.grid, environment, steps=PLAYBACK_STEPS, seed=71, runs=PLAYBACK_RUNS)
    with_plan_grid = _apply_placements(scenario.grid, classical["placements"])
    with_plan_forecast = run_stochastic_forecast(with_plan_grid, environment, steps=PLAYBACK_STEPS, seed=71, runs=PLAYBACK_RUNS)
    comparison = _build_playback_comparison(baseline_forecast, with_plan_forecast)
    classical["explanation"] = _plan_explanation("challenge", "recommended", baseline_forecast["summary"], with_plan_forecast["summary"])

    recommendation_status = "recommended" if classical["objective_after"] < classical["objective_before"] else "no_clear_gain"
    recommendation_reason = (
        "Accepted because it lowers the challenge adjacency cost on the full 10x10 graph with strict K=10 placement."
        if recommendation_status == "recommended"
        else "No improvement over the baseline challenge graph was found under the strict K=10 placement rule."
    )
    graph = classical["challenge_graph"]
    results = {
        "mode": CHALLENGE_MODE,
        "objective": {
            "name": "wildfire_challenge_cost",
            "description": "Minimize surviving dry-brush adjacency links under strict K=10 placement using C = sum_(i,j in E)(1-x_i)(1-x_j) + (sum_i x_i - 10)^2.",
            "budget_enforced_k": enforced_budget,
            "challenge_grid_size": "10x10",
            "flammable_semantics": "dry_brush and ignition are treated as the challenge fire-path graph; intervention is the active protected placement.",
            "spatial_to_quantum_mapping": "Each shortlisted challenge cell maps to one qubit in the reduced QAOA subproblem derived from the same adjacency graph.",
        },
        "baseline": {"metrics": classical["metrics_before"], "objective_score": classical["objective_before"]},
        "classical": classical,
        "quantum": quantum,
        "recommended_plan": classical,
        "comparison_playback": comparison,
    }
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": CHALLENGE_MODE,
        "recommended_mode": "challenge_full_plan",
        "recommended_plan_type": "challenge",
        "recommendation_status": recommendation_status,
        "recommendation_reason": recommendation_reason,
        "budget_requested_k": payload["intervention_budget_k"],
        "budget_enforced_k": enforced_budget,
        "challenge_cost_before": classical["metrics_before"]["challenge_cost"],
        "challenge_cost_after": classical["metrics_after"]["challenge_cost"],
        "K_used": len(classical["placements"]),
        "link_reduction": classical["metrics_before"]["surviving_edges"] - classical["metrics_after"]["surviving_edges"],
        "disrupted_edges": classical["metrics_before"]["surviving_edges"] - classical["metrics_after"]["surviving_edges"],
        "connectivity_reduction": classical["metrics_before"]["surviving_edges"] - classical["metrics_after"]["surviving_edges"],
        "challenge_graph_nodes": graph["node_count"],
        "challenge_graph_edges": graph["edge_count"],
        "full_scale_scope": "Challenge mode evaluates the full 10x10 adjacency graph classically under the posted K=10 placement rule.",
        "reduced_quantum_scope": quantum["scope"],
        "challenge_mode_note": "Challenge mode matches the posted adjacency disruption framing. Planning mode remains available for forecast-aware preseason analysis.",
        "plan_explanation": classical["explanation"],
        "difference_summary": comparison["difference_summary"],
    }
    run = OptimizationRun(
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        request_json={**payload, "mode": CHALLENGE_MODE, "intervention_budget_k": enforced_budget},
        results_json=results,
        summary_json=summary,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def create_optimization_run(db: Session, scenario: Scenario, payload: dict) -> OptimizationRun:
    mode = payload.get("mode", PLANNING_MODE)
    requested_budget = payload["intervention_budget_k"]
    enforced_budget = min(CHALLENGE_BUDGET, requested_budget, len(normalize_grid(scenario.grid)) * len(normalize_grid(scenario.grid)[0]))
    if mode == CHALLENGE_MODE:
        return _create_challenge_run(db, scenario, payload, enforced_budget)

    environment = build_environment(default_environment(scenario))
    return _create_planning_run(db, scenario, payload, enforced_budget, environment)
