# MarketMind-Q Results Summary

This report is generated from `python -m src.make_report`.

## Best Classical

| model   | model_family   | execution_mode   |   train_size |   feature_dim | split_id          | cutoff_date   |   balanced_accuracy |       f1 |   roc_auc |   precision_top_decile |   signal_return_mean |   signal_sharpe |   max_drawdown |   train_seconds |   infer_seconds |   qubits |   kernel_circuit_depth |   kernel_two_qubit_gates |   shots |   selected_features | market_regime   | confusion_matrix   |
|:--------|:---------------|:-----------------|-------------:|--------------:|:------------------|:--------------|--------------------:|---------:|----------:|-----------------------:|---------------------:|----------------:|---------------:|----------------:|----------------:|---------:|-----------------------:|-------------------------:|--------:|--------------------:|:----------------|:-------------------|
| rbf_svm | classical      | sklearn          |           40 |           nan | split_00_train_40 | 2023-01-03    |                 0.5 | 0.688525 |  0.295739 |                   0.25 |           0.00498688 |         2.62773 |     -0.0213686 |      0.00253179 |      0.00107946 |      nan |                    nan |                      nan |     nan |                 nan | high_volatility | [[0, 19], [0, 21]] |

## Best Quantum

| model              | model_family   | execution_mode    |   train_size |   feature_dim | split_id          | cutoff_date   |   balanced_accuracy |       f1 |   roc_auc |   precision_top_decile |   signal_return_mean |   signal_sharpe |   max_drawdown |   train_seconds |   infer_seconds |   qubits |   kernel_circuit_depth |   kernel_two_qubit_gates |   shots | selected_features   | market_regime   | confusion_matrix   |
|:-------------------|:---------------|:------------------|-------------:|--------------:|:------------------|:--------------|--------------------:|---------:|----------:|-----------------------:|---------------------:|----------------:|---------------:|----------------:|----------------:|---------:|-----------------------:|-------------------------:|--------:|:--------------------|:----------------|:-------------------|
| quantum_kernel_svm | quantum        | statevector_exact |           40 |             2 | split_00_train_40 | 2023-01-03    |            0.382206 | 0.285714 |  0.290727 |                   0.25 |          -0.00159773 |        -1.11608 |     -0.0468386 |        0.443984 |        0.000532 |        2 |                     22 |                        6 |     nan | vol_5d,vol_20d      | high_volatility | [[10, 9], [16, 5]] |

## Top Rows By ROC-AUC

| model               | model_family   | execution_mode    |   train_size |   feature_dim | split_id          | cutoff_date   |   balanced_accuracy |       f1 |   roc_auc |   precision_top_decile |   signal_return_mean |   signal_sharpe |   max_drawdown |   train_seconds |   infer_seconds |   qubits |   kernel_circuit_depth |   kernel_two_qubit_gates |   shots | selected_features   | market_regime   | confusion_matrix    |
|:--------------------|:---------------|:------------------|-------------:|--------------:|:------------------|:--------------|--------------------:|---------:|----------:|-----------------------:|---------------------:|----------------:|---------------:|----------------:|----------------:|---------:|-----------------------:|-------------------------:|--------:|:--------------------|:----------------|:--------------------|
| rbf_svm             | classical      | sklearn           |           40 |           nan | split_00_train_40 | 2023-01-03    |            0.5      | 0.688525 |  0.295739 |                   0.25 |           0.00498688 |        2.62773  |     -0.0213686 |      0.00253179 |     0.00107946  |      nan |                    nan |                      nan |     nan | nan                 | high_volatility | [[0, 19], [0, 21]]  |
| quantum_kernel_svm  | quantum        | statevector_exact |           40 |             2 | split_00_train_40 | 2023-01-03    |            0.382206 | 0.285714 |  0.290727 |                   0.25 |          -0.00159773 |       -1.11608  |     -0.0468386 |      0.443984   |     0.000532    |        2 |                     22 |                        6 |     nan | vol_5d,vol_20d      | high_volatility | [[10, 9], [16, 5]]  |
| xgboost             | classical      | sklearn           |           40 |           nan | split_00_train_40 | 2023-01-03    |            0.288221 | 0.44     |  0.20802  |                   0.25 |           0.00157541 |        0.825329 |     -0.0802255 |      0.0380746  |     0.00121146  |      nan |                    nan |                      nan |     nan | nan                 | high_volatility | [[1, 18], [10, 11]] |
| random_forest       | classical      | sklearn           |           40 |           nan | split_00_train_40 | 2023-01-03    |            0.340852 | 0.458333 |  0.155388 |                   0.25 |           0.00221066 |        1.08208  |     -0.0719696 |      0.372914   |     0.0537797   |      nan |                    nan |                      nan |     nan | nan                 | high_volatility | [[3, 16], [10, 11]] |
| logistic_regression | classical      | sklearn           |           40 |           nan | split_00_train_40 | 2023-01-03    |            0.337093 | 0.129032 |  0.14787  |                   0    |          -0.00507092 |       -3.51427  |     -0.0760243 |      0.0114593  |     0.000273042 |      nan |                    nan |                      nan |     nan | nan                 | high_volatility | [[11, 8], [19, 2]]  |

## qBraid Compiler-Aware Results

| strategy        | execution_environment   |   rows |   mean_abs_probability_error |   max_abs_probability_error |   mean_hellinger_distance |   mean_depth |   mean_two_qubit_gates |
|:----------------|:------------------------|-------:|-----------------------------:|----------------------------:|--------------------------:|-------------:|-----------------------:|
| cirq_direct     | cirq_shots_1024         |     16 |                  0.0084164   |                 0.0209998   |               0.00902272  |           37 |                      8 |
| cirq_direct     | cirq_statevector        |     16 |                  7.02636e-08 |                 2.14944e-07 |               8.84273e-08 |           37 |                      8 |
| qasm2_roundtrip | qiskit_shots_1024       |     16 |                  0.0108792   |                 0.0209835   |               0.0109416   |           21 |                      9 |
| qasm2_roundtrip | qiskit_statevector      |     16 |                  0           |                 0           |               0           |           21 |                      9 |

## Figures

- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/smoke_figures/qml_edge_heatmap.png`
- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/smoke_figures/regime_breakdown.png`
- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/smoke_figures/confusion_matrices.png`
- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/smoke_figures/equity_curve.png`
- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/smoke_figures/score_cost_frontier.png`
