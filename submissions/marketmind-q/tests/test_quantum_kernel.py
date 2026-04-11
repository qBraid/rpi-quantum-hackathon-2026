from __future__ import annotations

import numpy as np
import pytest

from src.quantum_kernel import exact_kernel, postprocess_kernel


def test_kernel_postprocessing_symmetrizes_and_sets_train_diagonal():
    raw = np.array([[1.2, 0.2], [0.4, -0.5]])
    processed = postprocess_kernel(raw, train=True)
    assert np.all(processed >= 0.0)
    assert np.all(processed <= 1.0)
    assert np.allclose(processed, processed.T)
    assert np.allclose(np.diag(processed), 1.0)


def test_exact_quantum_kernel_shape_and_bounds():
    pytest.importorskip("qiskit")
    x_train = np.array([[0.0, 0.1], [0.2, 0.3]])
    x_test = np.array([[0.4, 0.5]])
    kernel = exact_kernel(x_test, x_train)
    assert kernel.shape == (1, 2)
    assert np.all(kernel >= 0.0)
    assert np.all(kernel <= 1.0)

