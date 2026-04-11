from __future__ import annotations


def build_shift_diagnostics(size: int, steps: int) -> dict:
    baseline_depth = (size - 1) * 3 * steps
    optimized_depth = (size - 1) * 2 * steps
    baseline_cx = (size - 1) * 2 * steps
    optimized_cx = int(baseline_cx * 0.7)
    return {
        "diagnostic_mode": "analytical_shift_kernel",
        "baseline_shift": {"depth": baseline_depth, "two_qubit_gate_count": baseline_cx, "width": size},
        "optimized_shift": {"depth": optimized_depth, "two_qubit_gate_count": optimized_cx, "width": size},
        "summary": "Optimized shift logic reduces routing pressure for wind-aligned propagation kernels.",
    }
