# MarketMind-Q Results Summary

This report is generated from `python -m src.make_report`.

## Best Classical

| model   | model_family   | execution_mode   |   train_size |   feature_dim | split_id          | cutoff_date   |   balanced_accuracy |      f1 |   roc_auc |   precision_top_decile |   signal_return_mean |   signal_sharpe |   max_drawdown |   train_seconds |   infer_seconds |   qubits |   kernel_circuit_depth |   kernel_two_qubit_gates |   shots |   selected_features | market_regime   | confusion_matrix      |
|:--------|:---------------|:-----------------|-------------:|--------------:|:------------------|:--------------|--------------------:|--------:|----------:|-----------------------:|---------------------:|----------------:|---------------:|----------------:|----------------:|---------:|-----------------------:|-------------------------:|--------:|--------------------:|:----------------|:----------------------|
| rbf_svm | classical      | sklearn          |           40 |           nan | split_04_train_40 | 2024-01-02    |            0.641443 | 0.46729 |  0.665336 |               0.590909 |           0.00205993 |        0.960561 |      -0.113606 |      0.00110729 |      0.00136396 |      nan |                    nan |                      nan |     nan |                 nan | low_volatility  | [[138, 24], [33, 25]] |

## Best Quantum

| model              | model_family   | execution_mode   |   train_size |   feature_dim | split_id          | cutoff_date   |   balanced_accuracy |       f1 |   roc_auc |   precision_top_decile |   signal_return_mean |   signal_sharpe |   max_drawdown |   train_seconds |   infer_seconds |   qubits |   kernel_circuit_depth |   kernel_two_qubit_gates |   shots | selected_features             | market_regime   | confusion_matrix     |
|:-------------------|:---------------|:-----------------|-------------:|--------------:|:------------------|:--------------|--------------------:|---------:|----------:|-----------------------:|---------------------:|----------------:|---------------:|----------------:|----------------:|---------:|-----------------------:|-------------------------:|--------:|:------------------------------|:----------------|:---------------------|
| quantum_kernel_svm | quantum        | noisy_1024       |           40 |             2 | split_00_train_40 | 2023-01-03    |            0.581166 | 0.537445 |   0.63931 |               0.545455 |          7.79693e-05 |       0.0247791 |      -0.250335 |        0.500127 |     0.000432167 |        2 |                     22 |                        6 |    1024 | ret_20d,relative_strength_20d | high_volatility | [[54, 88], [17, 61]] |

## Top Rows By ROC-AUC

| model               | model_family   | execution_mode    |   train_size |   feature_dim | split_id           | cutoff_date   |   balanced_accuracy |       f1 |   roc_auc |   precision_top_decile |   signal_return_mean |   signal_sharpe |   max_drawdown |   train_seconds |   infer_seconds |   qubits |   kernel_circuit_depth |   kernel_two_qubit_gates |   shots | selected_features             | market_regime   | confusion_matrix      |
|:--------------------|:---------------|:------------------|-------------:|--------------:|:-------------------|:--------------|--------------------:|---------:|----------:|-----------------------:|---------------------:|----------------:|---------------:|----------------:|----------------:|---------:|-----------------------:|-------------------------:|--------:|:------------------------------|:----------------|:----------------------|
| rbf_svm             | classical      | sklearn           |           40 |           nan | split_04_train_40  | 2024-01-02    |            0.641443 | 0.46729  |  0.665336 |               0.590909 |          0.00205993  |       0.960561  |      -0.113606 |      0.00110729 |     0.00136396  |      nan |                    nan |                      nan |     nan | nan                           | low_volatility  | [[138, 24], [33, 25]] |
| xgboost             | classical      | sklearn           |           40 |           nan | split_04_train_40  | 2024-01-02    |            0.57301  | 0.446429 |  0.642827 |               0.5      |         -0.0072807   |      -2.44684   |      -0.735242 |      0.0190282  |     0.00144167  |      nan |                    nan |                      nan |     nan | nan                           | low_volatility  | [[46, 116], [8, 50]]  |
| quantum_kernel_svm  | quantum        | noisy_1024        |           40 |             2 | split_00_train_40  | 2023-01-03    |            0.581166 | 0.537445 |  0.63931  |               0.545455 |          7.79693e-05 |       0.0247791 |      -0.250335 |      0.500127   |     0.000432167 |        2 |                     22 |                        6 |    1024 | ret_20d,relative_strength_20d | high_volatility | [[54, 88], [17, 61]]  |
| rbf_svm             | classical      | sklearn           |          160 |           nan | split_07_train_160 | 2024-10-01    |            0.583916 | 0.564103 |  0.635183 |               0.545455 |         -0.0018139   |      -0.870003  |      -0.417254 |      0.00446917 |     0.00351     |      nan |                    nan |                      nan |     nan | nan                           | low_volatility  | [[24, 119], [0, 77]]  |
| quantum_kernel_svm  | quantum        | statevector_exact |           40 |             2 | split_00_train_40  | 2023-01-03    |            0.588841 | 0.540541 |  0.633397 |               0.5      |          0.000432157 |       0.13688   |      -0.236757 |      0.500397   |     0.00122075  |        2 |                     22 |                        6 |     nan | ret_20d,relative_strength_20d | high_volatility | [[58, 84], [18, 60]]  |
| quantum_kernel_svm  | quantum        | shots_1024        |           40 |             2 | split_00_train_40  | 2023-01-03    |            0.595251 | 0.547085 |  0.632087 |               0.454545 |          0.000612664 |       0.193817  |      -0.236757 |      0.500154   |     0.000440042 |        2 |                     22 |                        6 |    1024 | ret_20d,relative_strength_20d | high_volatility | [[58, 84], [17, 61]]  |
| logistic_regression | classical      | sklearn           |           40 |           nan | split_04_train_40  | 2024-01-02    |            0.551298 | 0.44     |  0.624628 |               0.409091 |         -0.00708307  |      -2.53682   |      -0.759847 |      0.00166233 |     0.000216792 |      nan |                    nan |                      nan |     nan | nan                           | low_volatility  | [[25, 137], [3, 55]]  |
| random_forest       | classical      | sklearn           |           40 |           nan | split_04_train_40  | 2024-01-02    |            0.540336 | 0.422907 |  0.610047 |               0.454545 |         -0.00821216  |      -2.79266   |      -0.777383 |      0.28503    |     0.0537247   |      nan |                    nan |                      nan |     nan | nan                           | low_volatility  | [[41, 121], [10, 48]] |

## qBraid Compiler-Aware Results

| strategy        | execution_environment   |   rows |   mean_abs_probability_error |   max_abs_probability_error |   mean_hellinger_distance |   mean_depth |   mean_two_qubit_gates |
|:----------------|:------------------------|-------:|-----------------------------:|----------------------------:|--------------------------:|-------------:|-----------------------:|
| cirq_direct     | cirq_shots_1024         |     16 |                  0.0084164   |                 0.0209998   |               0.00902272  |           37 |                      8 |
| cirq_direct     | cirq_statevector        |     16 |                  7.02636e-08 |                 2.14944e-07 |               8.84273e-08 |           37 |                      8 |
| qasm2_roundtrip | qiskit_shots_1024       |     16 |                  0.0108792   |                 0.0209835   |               0.0109416   |           21 |                      9 |
| qasm2_roundtrip | qiskit_statevector      |     16 |                  0           |                 0           |               0           |           21 |                      9 |

## Figures

- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/figures/qml_edge_heatmap.png`
- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/figures/regime_breakdown.png`
- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/figures/confusion_matrices.png`
- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/figures/equity_curve.png`
- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/figures/score_cost_frontier.png`
- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/figures/qbraid_quality_cost.png`
- `/Users/tazeemmahashin/Downloads/QuantumHackathon/finance-qml-benchmark/results/figures/qbraid_strategy_resources.png`
