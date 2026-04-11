"""qBraid compiler-aware benchmark for MarketMind-Q quantum kernels."""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(__file__).resolve().parents[1] / ".cache"))

import numpy as np
import pandas as pd

from .config import load_config, project_path
from .constants import PROJECT_ROOT, RANDOM_STATE
from .features import read_dataset
from .quantum_kernel import make_compute_uncompute_circuit
from .splits import make_walk_forward_splits, prepare_features


@dataclass(frozen=True)
class KernelPair:
    pair_id: str
    pair_kind: str
    left: np.ndarray
    right: np.ndarray


def hellinger_bernoulli(p: float, q: float) -> float:
    p = float(np.clip(p, 0.0, 1.0))
    q = float(np.clip(q, 0.0, 1.0))
    return math.sqrt(
        max(
            0.0,
            1.0 - (math.sqrt(p * q) + math.sqrt((1.0 - p) * (1.0 - q))),
        )
    )


def select_best_quantum_row(metrics: pd.DataFrame) -> pd.Series:
    candidates = metrics[
        (metrics["model"] == "quantum_kernel_svm")
        & (metrics["execution_mode"] == "statevector_exact")
        & (metrics["model_family"] == "quantum")
    ].copy()
    if candidates.empty:
        raise ValueError("No quantum_kernel_svm statevector_exact rows found.")
    return candidates.sort_values("roc_auc", ascending=False).iloc[0]


def reconstruct_best_split(config: Dict[str, Any], *, root: Path = PROJECT_ROOT) -> tuple[Any, Any, pd.Series]:
    dataset = read_dataset(project_path(config["dataset_path"], root=root))
    if config.get("tickers"):
        dataset = dataset[dataset["ticker"].isin(config["tickers"])].copy()
    metrics = pd.read_csv(project_path(config["metrics_path"], root=root))
    best = select_best_quantum_row(metrics)
    train_size = int(best["train_size"])
    feature_dim = int(best["feature_dim"])
    bundles = make_walk_forward_splits(
        dataset,
        cutoffs=config["cutoffs"],
        train_size=train_size,
        test_days=int(config.get("test_days", 20)),
    )
    for bundle in bundles:
        if bundle.split_id == best["split_id"]:
            prepared = prepare_features(bundle.train, bundle.test, feature_dim=feature_dim)
            return bundle, prepared, best
    raise ValueError(f"Could not reconstruct split {best['split_id']}.")


def deterministic_kernel_pairs(
    x_train: np.ndarray,
    x_test: np.ndarray,
    *,
    max_train_pairs: int = 8,
    max_test_pairs: int = 8,
) -> List[KernelPair]:
    pairs: List[KernelPair] = []
    train_count = min(max_train_pairs, max(0, len(x_train) - 1))
    for index in range(train_count):
        pairs.append(
            KernelPair(
                pair_id=f"train_train_{index:02d}",
                pair_kind="train_train",
                left=x_train[index],
                right=x_train[(index + 1) % len(x_train)],
            )
        )
    test_count = min(max_test_pairs, len(x_test), len(x_train))
    for index in range(test_count):
        pairs.append(
            KernelPair(
                pair_id=f"test_train_{index:02d}",
                pair_kind="test_train",
                left=x_test[index],
                right=x_train[index % len(x_train)],
            )
        )
    return pairs


def qiskit_zero_probability(circuit: Any) -> float:
    from qiskit.quantum_info import Statevector

    clean = circuit.remove_final_measurements(inplace=False)
    state = Statevector.from_instruction(clean)
    probabilities = state.probabilities_dict()
    return float(probabilities.get("0" * clean.num_qubits, 0.0))


def qiskit_resource_metrics(circuit: Any) -> Dict[str, int]:
    two_qubit = 0
    measurements = 0
    for instruction in circuit.data:
        operation = instruction.operation
        if getattr(operation, "num_qubits", 0) == 2:
            two_qubit += 1
        if operation.name == "measure":
            measurements += 1
    return {
        "qubits": int(circuit.num_qubits),
        "depth": int(circuit.depth() or 0),
        "two_qubit_gates": int(two_qubit),
        "measurement_count": int(measurements),
    }


def qiskit_serialized_size(circuit: Any) -> int:
    try:
        from qiskit import qasm2

        return len(qasm2.dumps(circuit))
    except Exception:
        return len(str(circuit))


def cirq_resource_metrics(circuit: Any) -> Dict[str, int]:
    import cirq

    return {
        "qubits": int(len(circuit.all_qubits())),
        "depth": int(len(circuit)),
        "two_qubit_gates": int(sum(1 for op in circuit.all_operations() if len(op.qubits) == 2)),
        "measurement_count": int(sum(1 for op in circuit.all_operations() if cirq.is_measurement(op))),
    }


def cirq_serialized_size(circuit: Any) -> int:
    return len(str(circuit))


def cirq_zero_probability_statevector(circuit: Any) -> float:
    import cirq

    no_measure = cirq.drop_terminal_measurements(circuit)
    qubits = sorted(no_measure.all_qubits(), key=str)
    result = cirq.Simulator(seed=RANDOM_STATE).simulate(no_measure, qubit_order=qubits)
    return float(abs(result.final_state_vector[0]) ** 2)


def cirq_zero_probability_shots(circuit: Any, *, shots: int) -> float:
    import cirq

    result = cirq.Simulator(seed=RANDOM_STATE).run(circuit, repetitions=shots)
    if not result.measurements:
        return cirq_zero_probability_statevector(circuit)
    zero_mask: Optional[np.ndarray] = None
    for values in result.measurements.values():
        measurement_values = np.asarray(values)
        local_zero = np.all(measurement_values == 0, axis=1)
        zero_mask = local_zero if zero_mask is None else (zero_mask & local_zero)
    return float(np.mean(zero_mask)) if zero_mask is not None else 0.0


def qbraid_allclose(source: Any, compiled: Any) -> Optional[bool]:
    try:
        from qbraid.interface import circuits_allclose

        return bool(circuits_allclose(source, compiled, index_contig=True, allow_rev_qubits=True))
    except Exception:
        return None


def success_row(
    *,
    pair: KernelPair,
    strategy: str,
    execution_environment: str,
    program_type: str,
    source_p_zero: float,
    compiled_p_zero: float,
    resources: Dict[str, int],
    serialized_size: int,
    transpile_seconds: float,
    execution_seconds: float,
    shots: Optional[int],
    qbraid_allclose_value: Optional[bool],
    selected_features: Iterable[str],
    best_row: pd.Series,
) -> Dict[str, Any]:
    abs_error = abs(compiled_p_zero - source_p_zero)
    return {
        "pair_id": pair.pair_id,
        "pair_kind": pair.pair_kind,
        "strategy": strategy,
        "execution_environment": execution_environment,
        "program_type": program_type,
        "source_p_zero": source_p_zero,
        "compiled_p_zero": compiled_p_zero,
        "abs_probability_error": abs_error,
        "hellinger_distance": hellinger_bernoulli(source_p_zero, compiled_p_zero),
        "qubits": resources["qubits"],
        "depth": resources["depth"],
        "two_qubit_gates": resources["two_qubit_gates"],
        "measurement_count": resources["measurement_count"],
        "serialized_size": serialized_size,
        "transpile_seconds": transpile_seconds,
        "execution_seconds": execution_seconds,
        "shots": int(shots) if shots is not None else "",
        "status": "success",
        "error_message": "",
        "qbraid_allclose": "" if qbraid_allclose_value is None else bool(qbraid_allclose_value),
        "selected_features": ",".join(selected_features),
        "source_split_id": best_row["split_id"],
        "source_train_size": int(best_row["train_size"]),
        "source_feature_dim": int(best_row["feature_dim"]),
        "source_roc_auc": float(best_row["roc_auc"]),
    }


def failed_row(pair: KernelPair, *, strategy: str, error: Exception, best_row: pd.Series) -> Dict[str, Any]:
    return {
        "pair_id": pair.pair_id,
        "pair_kind": pair.pair_kind,
        "strategy": strategy,
        "execution_environment": "conversion",
        "program_type": "",
        "source_p_zero": "",
        "compiled_p_zero": "",
        "abs_probability_error": "",
        "hellinger_distance": "",
        "qubits": "",
        "depth": "",
        "two_qubit_gates": "",
        "measurement_count": "",
        "serialized_size": "",
        "transpile_seconds": "",
        "execution_seconds": "",
        "shots": "",
        "status": "failed",
        "error_message": f"{type(error).__name__}: {error}",
        "qbraid_allclose": "",
        "selected_features": "",
        "source_split_id": best_row["split_id"],
        "source_train_size": int(best_row["train_size"]),
        "source_feature_dim": int(best_row["feature_dim"]),
        "source_roc_auc": float(best_row["roc_auc"]),
    }


def qasm2_roundtrip_rows(pair: KernelPair, source: Any, source_p_zero: float, *, shots: int, selected_features: Iterable[str], best_row: pd.Series) -> List[Dict[str, Any]]:
    from qbraid import transpile

    start = time.perf_counter()
    qasm2_program = transpile(source, "qasm2", max_path_attempts=3)
    compiled = transpile(qasm2_program, "qiskit", max_path_attempts=3)
    transpile_seconds = time.perf_counter() - start
    resources = qiskit_resource_metrics(compiled)
    allclose_value = qbraid_allclose(source, compiled)
    rows: List[Dict[str, Any]] = []

    exec_start = time.perf_counter()
    compiled_p_zero = qiskit_zero_probability(compiled)
    rows.append(
        success_row(
            pair=pair,
            strategy="qasm2_roundtrip",
            execution_environment="qiskit_statevector",
            program_type="qiskit",
            source_p_zero=source_p_zero,
            compiled_p_zero=compiled_p_zero,
            resources=resources,
            serialized_size=qiskit_serialized_size(compiled),
            transpile_seconds=transpile_seconds,
            execution_seconds=time.perf_counter() - exec_start,
            shots=None,
            qbraid_allclose_value=allclose_value,
            selected_features=selected_features,
            best_row=best_row,
        )
    )

    exec_start = time.perf_counter()
    rng = np.random.default_rng(RANDOM_STATE)
    sampled_p_zero = float(rng.binomial(shots, np.clip(compiled_p_zero, 0.0, 1.0)) / shots)
    rows.append(
        success_row(
            pair=pair,
            strategy="qasm2_roundtrip",
            execution_environment="qiskit_shots_1024",
            program_type="qiskit",
            source_p_zero=source_p_zero,
            compiled_p_zero=sampled_p_zero,
            resources=resources,
            serialized_size=qiskit_serialized_size(compiled),
            transpile_seconds=transpile_seconds,
            execution_seconds=time.perf_counter() - exec_start,
            shots=shots,
            qbraid_allclose_value=allclose_value,
            selected_features=selected_features,
            best_row=best_row,
        )
    )
    return rows


def cirq_direct_rows(pair: KernelPair, source: Any, source_p_zero: float, *, shots: int, selected_features: Iterable[str], best_row: pd.Series) -> List[Dict[str, Any]]:
    from qbraid import transpile

    start = time.perf_counter()
    compiled = transpile(source, "cirq", max_path_attempts=3)
    transpile_seconds = time.perf_counter() - start
    resources = cirq_resource_metrics(compiled)
    serialized_size = cirq_serialized_size(compiled)
    allclose_value = qbraid_allclose(source, compiled)
    rows: List[Dict[str, Any]] = []

    exec_start = time.perf_counter()
    shot_p_zero = cirq_zero_probability_shots(compiled, shots=shots)
    rows.append(
        success_row(
            pair=pair,
            strategy="cirq_direct",
            execution_environment="cirq_shots_1024",
            program_type="cirq",
            source_p_zero=source_p_zero,
            compiled_p_zero=shot_p_zero,
            resources=resources,
            serialized_size=serialized_size,
            transpile_seconds=transpile_seconds,
            execution_seconds=time.perf_counter() - exec_start,
            shots=shots,
            qbraid_allclose_value=allclose_value,
            selected_features=selected_features,
            best_row=best_row,
        )
    )

    exec_start = time.perf_counter()
    exact_p_zero = cirq_zero_probability_statevector(compiled)
    rows.append(
        success_row(
            pair=pair,
            strategy="cirq_direct",
            execution_environment="cirq_statevector",
            program_type="cirq",
            source_p_zero=source_p_zero,
            compiled_p_zero=exact_p_zero,
            resources=resources,
            serialized_size=serialized_size,
            transpile_seconds=transpile_seconds,
            execution_seconds=time.perf_counter() - exec_start,
            shots=None,
            qbraid_allclose_value=allclose_value,
            selected_features=selected_features,
            best_row=best_row,
        )
    )
    return rows


def record_conversion_paths(output_path: Path) -> pd.DataFrame:
    from qbraid import ConversionGraph
    import qbraid

    graph = ConversionGraph()
    path_specs = [("qiskit", "qasm2"), ("qasm2", "qiskit"), ("qiskit", "cirq")]
    rows = []
    for source, target in path_specs:
        try:
            paths = graph.all_paths(source, target)
            shortest = graph.shortest_path(source, target)
            status = "success"
            error = ""
        except Exception as exc:
            paths = []
            shortest = ""
            status = "failed"
            error = f"{type(exc).__name__}: {exc}"
        rows.append(
            {
                "source": source,
                "target": target,
                "path_count": len(paths),
                "paths": " | ".join(map(str, paths)),
                "shortest_path": str(shortest),
                "status": status,
                "error_message": error,
                "qbraid_version": getattr(qbraid, "__version__", "unknown"),
            }
        )
    frame = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return frame


def aggregate_quality(metrics: pd.DataFrame) -> pd.DataFrame:
    successful = metrics[metrics["status"] == "success"].copy()
    if successful.empty:
        return pd.DataFrame()
    grouped = successful.groupby(["strategy", "execution_environment", "program_type"], as_index=False).agg(
        mean_abs_probability_error=("abs_probability_error", "mean"),
        max_abs_probability_error=("abs_probability_error", "max"),
        mean_hellinger_distance=("hellinger_distance", "mean"),
        mean_depth=("depth", "mean"),
        mean_two_qubit_gates=("two_qubit_gates", "mean"),
        mean_transpile_seconds=("transpile_seconds", "mean"),
        mean_execution_seconds=("execution_seconds", "mean"),
        rows=("pair_id", "count"),
    )
    return grouped


def _load_plotting():
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="whitegrid", context="talk")
    return plt, sns


def plot_qbraid_figures(metrics: pd.DataFrame, figures_dir: Path) -> List[Path]:
    plt, sns = _load_plotting()
    figures_dir.mkdir(parents=True, exist_ok=True)
    successful = metrics[metrics["status"] == "success"].copy()
    if successful.empty:
        return []

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=successful,
        x="two_qubit_gates",
        y="abs_probability_error",
        hue="strategy",
        style="execution_environment",
        size="depth",
        ax=ax,
    )
    ax.set_title("qBraid output error vs compiled two-qubit cost")
    ax.set_xlabel("Compiled two-qubit gates")
    ax.set_ylabel("|compiled p(0) - source p(0)|")
    quality_path = figures_dir / "qbraid_quality_cost.png"
    fig.tight_layout()
    fig.savefig(quality_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    summary = successful.groupby(["strategy", "execution_environment"], as_index=False).agg(
        depth=("depth", "mean"),
        two_qubit_gates=("two_qubit_gates", "mean"),
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.barplot(data=summary, x="strategy", y="depth", hue="execution_environment", errorbar=None, ax=axes[0])
    axes[0].set_title("Mean compiled depth")
    axes[0].set_xlabel("")
    axes[0].tick_params(axis="x", rotation=20)
    sns.barplot(data=summary, x="strategy", y="two_qubit_gates", hue="execution_environment", errorbar=None, ax=axes[1])
    axes[1].set_title("Mean compiled two-qubit gates")
    axes[1].set_xlabel("")
    axes[1].tick_params(axis="x", rotation=20)
    resources_path = figures_dir / "qbraid_strategy_resources.png"
    fig.tight_layout()
    fig.savefig(resources_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return [quality_path, resources_path]


def run_qbraid_benchmark(config: Dict[str, Any], *, root: Path = PROJECT_ROOT) -> pd.DataFrame:
    qbraid_metrics_path = project_path(config["qbraid_metrics_path"], root=root)
    path_summary_path = project_path(config["qbraid_path_summary_path"], root=root)
    figures_dir = project_path(config["figures_dir"], root=root)
    bundle, prepared, best_row = reconstruct_best_split(config, root=root)
    pairs = deterministic_kernel_pairs(
        prepared.x_train_quantum,
        prepared.x_test_quantum,
        max_train_pairs=int(config.get("max_train_pairs", 8)),
        max_test_pairs=int(config.get("max_test_pairs", 8)),
    )
    shots = int(config.get("shots", 1024))
    rows: List[Dict[str, Any]] = []
    for pair in pairs:
        source = make_compute_uncompute_circuit(pair.left, pair.right)
        source_p_zero = qiskit_zero_probability(source)
        for strategy_fn, strategy_name in ((qasm2_roundtrip_rows, "qasm2_roundtrip"), (cirq_direct_rows, "cirq_direct")):
            try:
                rows.extend(
                    strategy_fn(
                        pair,
                        source,
                        source_p_zero,
                        shots=shots,
                        selected_features=prepared.selected_features,
                        best_row=best_row,
                    )
                )
            except Exception as exc:
                rows.append(failed_row(pair, strategy=strategy_name, error=exc, best_row=best_row))

    metrics = pd.DataFrame(rows)
    successful = metrics[metrics["status"] == "success"]
    if successful.empty:
        qbraid_metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics.to_csv(qbraid_metrics_path, index=False)
        raise SystemExit("All qBraid compilation strategies failed.")

    aggregate = aggregate_quality(metrics)
    metrics = metrics.merge(
        aggregate,
        on=["strategy", "execution_environment", "program_type"],
        how="left",
    )
    qbraid_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(qbraid_metrics_path, index=False)
    record_conversion_paths(path_summary_path)
    plot_qbraid_figures(metrics, figures_dir)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Run qBraid compiler-aware benchmark for MarketMind-Q.")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "configs" / "qbraid.yaml"))
    args = parser.parse_args()
    metrics = run_qbraid_benchmark(load_config(args.config))
    successful = metrics[metrics["status"] == "success"]
    print(
        json.dumps(
            {
                "rows": len(metrics),
                "successful_rows": len(successful),
                "strategies": sorted(metrics["strategy"].unique().tolist()),
                "execution_environments": sorted(successful["execution_environment"].unique().tolist()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
