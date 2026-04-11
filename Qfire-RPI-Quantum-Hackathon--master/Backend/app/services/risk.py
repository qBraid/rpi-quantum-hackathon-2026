from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.models import RiskRun, Scenario
from app.schemas.common import GridCellScore
from app.services.wildfire_model import (
    CELL_LIBRARY,
    build_environment,
    default_environment,
    local_hazard_features,
    normalize_grid,
    run_stochastic_forecast,
)

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "fuel_load",
    "base_ignitability",
    "local_fuel_density",
    "distance_risk",
    "wind_exposure",
    "slope_factor",
    "treated",
    "connectivity_proxy",
]
DEFAULT_HORIZON_STEPS = 3
DEFAULT_SAMPLE_COUNT = 18
QML_TRAIN_LIMIT = 96


@dataclass
class DatasetBundle:
    feature_names: list[str]
    train_x: np.ndarray
    test_x: np.ndarray
    train_y: np.ndarray
    test_y: np.ndarray
    scoring_x: np.ndarray
    scoring_refs: list[tuple[int, int, str]]
    profiles: list[dict]
    summary: dict


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _variant_grid(base_grid: list[list[str]], seed: int) -> list[list[str]]:
    rng = np.random.default_rng(seed)
    grid = normalize_grid(base_grid)
    for row, line in enumerate(grid):
        for col, state in enumerate(line):
            roll = float(rng.random())
            if state == "dry_brush":
                if roll < 0.08:
                    grid[row][col] = "grass"
                elif roll < 0.14:
                    grid[row][col] = "shrub"
                elif roll < 0.19:
                    grid[row][col] = "protected"
            elif state == "tree":
                if roll < 0.08:
                    grid[row][col] = "shrub"
                elif roll < 0.14:
                    grid[row][col] = "grass"
            elif state == "empty" and roll < 0.08:
                grid[row][col] = "grass"
            elif state == "protected" and roll < 0.05:
                grid[row][col] = "intervention"
    return grid


def _sample_profiles(base_environment: dict, sample_count: int, horizon_steps: int, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    profiles: list[dict] = []
    for idx in range(sample_count):
        profiles.append(
            {
                "profile_id": idx,
                "horizon_steps": horizon_steps,
                "dryness": round(float(_clip(base_environment["dryness"] + rng.normal(0.0, 0.05), 0.25, 0.98)), 3),
                "spread_sensitivity": round(float(_clip(base_environment["spread_sensitivity"] + rng.normal(0.0, 0.05), 0.25, 0.98)), 3),
                "wind_speed": round(float(_clip(base_environment["wind_speed"] + rng.normal(0.0, 0.06), 0.15, 1.0)), 3),
                "wind_direction": str(rng.choice(directions)),
                "spotting_likelihood": round(float(_clip(base_environment["spotting_likelihood"] + rng.normal(0.0, 0.02), 0.0, 0.2)), 3),
                "slope_influence": round(float(base_environment["slope_influence"]), 3),
            }
        )
    return profiles


def _cell_feature_vector(grid: list[list[str]], row: int, col: int, environment: dict) -> np.ndarray:
    features = local_hazard_features(grid, row, col, environment)
    return np.array(
        [
            features["fuel_load"],
            features["base_ignitability"],
            features["local_fuel_density"],
            features["distance_risk"],
            features["wind_exposure"],
            features["slope_factor"],
            features["treated"],
            features["connectivity_proxy"],
        ],
        dtype=float,
    )


def _ensemble_labels(grid: list[list[str]], environment: dict, horizon_steps: int, seed: int) -> np.ndarray:
    forecast = run_stochastic_forecast(grid, environment, steps=horizon_steps, seed=seed, runs=12)
    label_grid = np.zeros((len(grid), len(grid[0])), dtype=int)
    for cell in forecast["burn_probability_map"]:
        label_grid[cell["row"], cell["col"]] = int(cell["probability"] >= 0.3)
    return label_grid


def _build_dataset(
    scenario: Scenario,
    horizon_steps: int,
    sample_count: int,
    threshold: float,
    seed: int,
) -> DatasetBundle:
    base_environment = default_environment(scenario)
    profiles = _sample_profiles(base_environment, sample_count, horizon_steps, seed)
    normalized_scenario = normalize_grid(scenario.grid)
    effective_horizon = horizon_steps
    features: list[np.ndarray]
    labels: list[int]
    scoring_samples: list[np.ndarray] = []
    scoring_refs: list[tuple[int, int, str]] = []

    iterations = 0
    while iterations < 8:
        iterations += 1
        features = []
        labels = []
        for profile in profiles:
            training_grid = _variant_grid(normalized_scenario, seed + profile["profile_id"] * 31)
            environment = build_environment(base_environment, **profile)
            labels_grid = _ensemble_labels(training_grid, environment, effective_horizon, seed + profile["profile_id"] * 97)
            for row, line in enumerate(training_grid):
                for col, state in enumerate(line):
                    features.append(_cell_feature_vector(training_grid, row, col, environment))
                    labels.append(int(labels_grid[row, col]))
        counts = np.bincount(np.asarray(labels, dtype=int), minlength=2)
        if len(np.unique(labels)) > 1 and int(counts.min()) >= 10:
            break
        # If heavily biased towards 1s (saturated), reduce horizon
        if counts[1] > counts[0] * 3 and effective_horizon > 1:
            effective_horizon -= 1
        # If heavily biased towards 0s (no spread), increase horizon
        elif counts[0] > counts[1] * 3 and effective_horizon < 8:
            effective_horizon += 1
        else:
            break

    scoring_environment = build_environment(base_environment)
    preview = run_stochastic_forecast(normalized_scenario, scoring_environment, steps=effective_horizon, seed=seed, runs=16)
    for row, line in enumerate(normalized_scenario):
        for col, state in enumerate(line):
            scoring_samples.append(_cell_feature_vector(normalized_scenario, row, col, scoring_environment))
            scoring_refs.append((row, col, state))

    x = np.asarray(features, dtype=float)
    y = np.asarray(labels, dtype=int)
    train_x, test_x, train_y, test_y = train_test_split(
        x,
        y,
        test_size=0.3,
        random_state=seed,
        stratify=y if len(np.unique(y)) > 1 else None,
    )
    summary = {
        "classification_task": f"Predict whether a cell belongs to the early ignition corridor within {effective_horizon} forecast steps.",
        "effective_label_horizon_steps": effective_horizon,
        "label_definition": f"label=1 when ensemble burn probability is at least 0.3 by step {effective_horizon}.",
        "feature_names": FEATURE_NAMES,
        "sample_count": int(len(y)),
        "positive_samples": int(y.sum()),
        "negative_samples": int(len(y) - int(y.sum())),
        "positive_rate": round(float(y.mean()), 4),
        "train_samples": int(len(train_y)),
        "test_samples": int(len(test_y)),
        "requested_horizon_steps": horizon_steps,
        "dataset_generation": "Labels are generated from the shared stochastic wildfire ensemble model under varied planning conditions.",
        "sampled_profiles": profiles,
        "decision_threshold": threshold,
        "preview_burn_probability_map": preview["burn_probability_map"],
        "preview_likely_corridors": preview["summary"]["likely_spread_corridors"],
    }
    return DatasetBundle(
        feature_names=FEATURE_NAMES,
        train_x=train_x,
        test_x=test_x,
        train_y=train_y,
        test_y=test_y,
        scoring_x=np.asarray(scoring_samples, dtype=float),
        scoring_refs=scoring_refs,
        profiles=profiles,
        summary=summary,
    )


def _classification_metrics(y_true: np.ndarray, probabilities: np.ndarray, threshold: float, runtime_ms: float) -> dict:
    predictions = (probabilities >= threshold).astype(int)
    return {
        "accuracy": round(float(accuracy_score(y_true, predictions)), 4),
        "precision": round(float(precision_score(y_true, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, predictions, zero_division=0)), 4),
        "auroc": round(float(roc_auc_score(y_true, probabilities)), 4) if len(np.unique(y_true)) > 1 else None,
        "positive_prediction_rate": round(float(predictions.mean()), 4),
        "runtime_ms": round(float(runtime_ms), 2),
    }


def _grid_scores_from_probabilities(probabilities: np.ndarray, refs: list[tuple[int, int, str]]) -> tuple[list[dict], list[dict]]:
    scores: list[GridCellScore] = []
    for probability, (row, col, state) in zip(probabilities, refs, strict=False):
        confidence = min(1.0, abs(float(probability) - 0.5) * 2.0)
        scores.append(
            GridCellScore(
                row=row,
                col=col,
                state=state,
                score=round(float(probability), 4),
                confidence=round(float(confidence), 4),
            )
        )
    top_hotspots = sorted(scores, key=lambda item: item.score, reverse=True)[:10]
    return [item.model_dump() for item in scores], [item.model_dump() for item in top_hotspots]


def _balanced_subset(x: np.ndarray, y: np.ndarray, limit: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    positives = np.where(y == 1)[0]
    negatives = np.where(y == 0)[0]
    if len(positives) == 0 or len(negatives) == 0 or len(y) <= limit:
        return x, y
    rng = np.random.default_rng(seed)
    take = max(1, min(len(positives), len(negatives), limit // 2))
    chosen = np.concatenate([rng.choice(positives, size=take, replace=False), rng.choice(negatives, size=take, replace=False)])
    rng.shuffle(chosen)
    return x[chosen], y[chosen]


class VariationalQuantumClassifier:
    def __init__(self, seed: int):
        self.seed = seed
        self.scaler = StandardScaler()
        self.parameters = np.zeros(6, dtype=float)
        self.training_samples = 0

    def _normalize(self, x: np.ndarray) -> np.ndarray:
        scaled = self.scaler.transform(x[:, :4])
        return np.clip(np.tanh(scaled), -1.0, 1.0)

    def _probability(self, vector: np.ndarray, parameters: np.ndarray) -> float:
        circuit = QuantumCircuit(2)
        circuit.ry(math.pi * vector[0], 0)
        circuit.rz(math.pi * vector[1], 0)
        circuit.ry(math.pi * vector[2], 1)
        circuit.rz(math.pi * vector[3], 1)
        circuit.cz(0, 1)
        circuit.ry(parameters[0], 0)
        circuit.rz(parameters[1], 0)
        circuit.ry(parameters[2], 1)
        circuit.rz(parameters[3], 1)
        circuit.cx(0, 1)
        circuit.ry(parameters[4], 0)
        circuit.ry(parameters[5], 1)
        probabilities = Statevector.from_instruction(circuit).probabilities()
        return float(probabilities[2] + probabilities[3])

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        self.scaler.fit(x[:, :4])
        normalized = self._normalize(x)
        rng = np.random.default_rng(self.seed)
        self.parameters = rng.uniform(-math.pi, math.pi, size=6)
        self.training_samples = int(len(y))

        def objective(parameters: np.ndarray) -> float:
            predictions = np.array([self._probability(vector, parameters) for vector in normalized], dtype=float)
            bounded = np.clip(predictions, 1e-5, 1 - 1e-5)
            return float(np.mean(-(y * np.log(bounded) + (1 - y) * np.log(1 - bounded))))

        result = minimize(objective, self.parameters, method="COBYLA", options={"maxiter": 40, "rhobeg": 0.6})
        self.parameters = result.x
        if not result.success:
            logger.warning("QML optimization did not fully converge: %s", result.message)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        normalized = self._normalize(x)
        return np.array([self._probability(vector, self.parameters) for vector in normalized], dtype=float)


def _run_classical(dataset: DatasetBundle, threshold: float) -> dict:
    started = perf_counter()
    model = Pipeline([("scaler", StandardScaler()), ("classifier", LogisticRegression(max_iter=400, class_weight="balanced"))])
    model.fit(dataset.train_x, dataset.train_y)
    test_probabilities = model.predict_proba(dataset.test_x)[:, 1]
    scoring_probabilities = model.predict_proba(dataset.scoring_x)[:, 1]
    grid_scores, top_hotspots = _grid_scores_from_probabilities(scoring_probabilities, dataset.scoring_refs)
    return {
        "mode": "classical",
        "task": dataset.summary["classification_task"],
        "feature_names": dataset.feature_names,
        "model": {
            "family": "logistic_regression",
            "source": "scikit-learn",
            "notes": "Planning-grade baseline trained on ensemble-derived ignition-corridor labels from the shared wildfire model.",
        },
        "grid_scores": grid_scores,
        "top_hotspots": top_hotspots,
        "metrics": {
            **_classification_metrics(dataset.test_y, test_probabilities, threshold, (perf_counter() - started) * 1000),
            "training_samples": int(len(dataset.train_y)),
            "test_samples": int(len(dataset.test_y)),
            "practicality": "Fastest and most repeatable model for scenario analysis.",
        },
        "_test_probabilities": test_probabilities.tolist(),
        "_scoring_probabilities": scoring_probabilities.tolist(),
    }


def _run_quantum(dataset: DatasetBundle, threshold: float, seed: int) -> dict:
    started = perf_counter()
    train_x, train_y = _balanced_subset(dataset.train_x, dataset.train_y, QML_TRAIN_LIMIT, seed)
    model = VariationalQuantumClassifier(seed)
    model.fit(train_x, train_y)
    test_probabilities = model.predict_proba(dataset.test_x)
    scoring_probabilities = model.predict_proba(dataset.scoring_x)
    grid_scores, top_hotspots = _grid_scores_from_probabilities(scoring_probabilities, dataset.scoring_refs)
    return {
        "mode": "quantum",
        "task": dataset.summary["classification_task"],
        "feature_names": dataset.feature_names[:4],
        "model": {
            "family": "variational_quantum_classifier",
            "source": "qiskit",
            "qubits": 2,
            "ansatz_depth": 2,
            "notes": "Shallow VQC on a reduced feature subset chosen from the same shared wildfire semantics.",
        },
        "grid_scores": grid_scores,
        "top_hotspots": top_hotspots,
        "metrics": {
            **_classification_metrics(dataset.test_y, test_probabilities, threshold, (perf_counter() - started) * 1000),
            "training_samples": int(model.training_samples),
            "test_samples": int(len(dataset.test_y)),
            "practicality": "Real QML comparator, but slower and limited to a compact feature subset.",
        },
        "_test_probabilities": test_probabilities.tolist(),
        "_scoring_probabilities": scoring_probabilities.tolist(),
    }


def _run_hybrid(classical: dict, quantum: dict, dataset: DatasetBundle, threshold: float) -> dict:
    started = perf_counter()
    test_probs = np.clip((np.asarray(classical["_test_probabilities"]) + np.asarray(quantum["_test_probabilities"])) / 2.0, 0.0, 1.0)
    scoring_probs = np.clip((np.asarray(classical["_scoring_probabilities"]) + np.asarray(quantum["_scoring_probabilities"])) / 2.0, 0.0, 1.0)
    grid_scores, top_hotspots = _grid_scores_from_probabilities(scoring_probs, dataset.scoring_refs)
    return {
        "mode": "hybrid",
        "task": dataset.summary["classification_task"],
        "feature_names": dataset.feature_names,
        "model": {"family": "probability_ensemble", "source": "classical+qiskit", "notes": "Average of classical and QML probabilities on the same corridor task."},
        "grid_scores": grid_scores,
        "top_hotspots": top_hotspots,
        "metrics": {
            **_classification_metrics(dataset.test_y, test_probs, threshold, (perf_counter() - started) * 1000),
            "training_samples": int(dataset.summary["train_samples"]),
            "test_samples": int(len(dataset.test_y)),
            "practicality": "Useful when analysts want conservative agreement across the two modeling styles.",
        },
    }


def _public_result(result: dict) -> dict:
    return {key: value for key, value in result.items() if not key.startswith("_")}


def create_risk_run(db: Session, scenario: Scenario, payload: dict) -> RiskRun:
    modes = payload.get("modes") or ["classical", "quantum", "hybrid"]
    threshold = float(payload.get("threshold", 0.5))
    horizon_steps = int(payload.get("horizon_steps", DEFAULT_HORIZON_STEPS))
    sample_count = int(payload.get("sample_count", DEFAULT_SAMPLE_COUNT))
    seed = int(payload.get("seed", 17))
    dataset = _build_dataset(scenario, horizon_steps, sample_count, threshold, seed)

    classical = _run_classical(dataset, threshold)
    quantum = _run_quantum(dataset, threshold, seed)
    hybrid = _run_hybrid(classical, quantum, dataset, threshold)
    raw_results = {"classical": classical, "quantum": quantum, "hybrid": hybrid}
    results = {mode: _public_result(raw_results[mode]) for mode in modes}

    comparison = [
        {
            "mode": mode,
            "accuracy": results[mode]["metrics"]["accuracy"],
            "precision": results[mode]["metrics"]["precision"],
            "recall": results[mode]["metrics"]["recall"],
            "f1": results[mode]["metrics"]["f1"],
            "auroc": results[mode]["metrics"]["auroc"],
            "runtime_ms": results[mode]["metrics"]["runtime_ms"],
            "practicality": results[mode]["metrics"]["practicality"],
        }
        for mode in modes
    ]
    best_mode = max(comparison, key=lambda item: (item["f1"], item["accuracy"]))["mode"]
    recommended_mode = "classical" if best_mode != "classical" and results["classical"]["metrics"]["f1"] >= results[best_mode]["metrics"]["f1"] - 0.03 else best_mode
    summary = {
        "recommended_mode": recommended_mode,
        "most_practical_mode": "classical",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification_task": dataset.summary["classification_task"],
        "dataset": dataset.summary,
        "comparison": comparison,
        "conclusion": (
            f"{recommended_mode.title()} produced the strongest planning-grade corridor classification on the held-out split. "
            "The labels, forecast assumptions, and optimization semantics now all come from the same shared wildfire model."
        ),
        "planning_grade_note": "Comparative scenario-analysis model for pre-season planning. It should not be used as an operational fire prediction system.",
    }
    run = RiskRun(
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        modes_json=modes,
        request_json={"scenario_id": scenario.id, "modes": modes, "threshold": threshold, "horizon_steps": horizon_steps, "sample_count": sample_count, "seed": seed},
        results_json=results,
        summary_json=summary,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
