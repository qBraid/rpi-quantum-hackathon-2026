"""Walk-forward split and preprocessing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from .constants import FEATURE_COLUMNS, RANDOM_STATE


@dataclass(frozen=True)
class SplitBundle:
    split_id: str
    cutoff_date: pd.Timestamp
    train: pd.DataFrame
    test: pd.DataFrame


@dataclass
class PreparedFeatures:
    x_train_classical: np.ndarray
    x_test_classical: np.ndarray
    x_train_quantum: np.ndarray
    x_test_quantum: np.ndarray
    y_train: np.ndarray
    y_test: np.ndarray
    selected_features: List[str]


def class_balanced_recent_sample(
    candidates: pd.DataFrame,
    *,
    train_size: int,
    date_column: str = "date",
    target_column: str = "target",
) -> pd.DataFrame:
    """Return the most recent class-balanced training sample."""
    if train_size % 2 != 0:
        raise ValueError("train_size must be even for class-balanced sampling.")
    per_class = train_size // 2
    samples = []
    for label in (0, 1):
        label_rows = candidates[candidates[target_column] == label].sort_values(date_column)
        if len(label_rows) < per_class:
            raise ValueError(f"Need {per_class} rows for class {label}, found {len(label_rows)}.")
        samples.append(label_rows.tail(per_class))
    sampled = pd.concat(samples, axis=0)
    return sampled.sort_values([date_column, "ticker"]).reset_index(drop=True)


def make_walk_forward_splits(
    dataset: pd.DataFrame,
    *,
    cutoffs: Iterable[str],
    train_size: int,
    test_days: int,
    date_column: str = "date",
) -> List[SplitBundle]:
    """Build date-respecting, class-balanced walk-forward splits."""
    data = dataset.copy()
    data[date_column] = pd.to_datetime(data[date_column])
    unique_dates = sorted(data[date_column].drop_duplicates())
    bundles: List[SplitBundle] = []
    for index, raw_cutoff in enumerate(cutoffs):
        cutoff = pd.Timestamp(raw_cutoff)
        train_candidates = data[data[date_column] < cutoff]
        try:
            train = class_balanced_recent_sample(train_candidates, train_size=train_size, date_column=date_column)
        except ValueError:
            continue

        test_dates = [date for date in unique_dates if date >= cutoff][:test_days]
        test = data[data[date_column].isin(test_dates)].sort_values([date_column, "ticker"]).reset_index(drop=True)
        if test.empty or test["target"].nunique() < 2:
            continue
        bundles.append(
            SplitBundle(
                split_id=f"split_{index:02d}_train_{train_size}",
                cutoff_date=cutoff,
                train=train,
                test=test,
            )
        )
    return bundles


def prepare_features(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    feature_dim: int,
    feature_columns: list[str] | None = None,
    random_state: int = RANDOM_STATE,
) -> PreparedFeatures:
    """Fit all preprocessing only on training rows."""
    columns = feature_columns or FEATURE_COLUMNS
    x_train_raw = train[columns].to_numpy(dtype=float)
    x_test_raw = test[columns].to_numpy(dtype=float)
    y_train = train["target"].to_numpy(dtype=int)
    y_test = test["target"].to_numpy(dtype=int)

    imputer = SimpleImputer(strategy="median")
    x_train_imputed = imputer.fit_transform(x_train_raw)
    x_test_imputed = imputer.transform(x_test_raw)

    classical_scaler = StandardScaler()
    x_train_classical = classical_scaler.fit_transform(x_train_imputed)
    x_test_classical = classical_scaler.transform(x_test_imputed)

    if feature_dim > len(columns):
        raise ValueError("feature_dim cannot exceed number of feature columns.")
    scores = mutual_info_classif(x_train_classical, y_train, random_state=random_state)
    selected_indices = np.argsort(scores)[::-1][:feature_dim]
    selected_indices = np.sort(selected_indices)
    selected_features = [columns[index] for index in selected_indices]

    angle_scaler = MinMaxScaler(feature_range=(0.0, np.pi))
    x_train_quantum = angle_scaler.fit_transform(x_train_classical[:, selected_indices])
    x_test_quantum = angle_scaler.transform(x_test_classical[:, selected_indices])
    x_test_quantum = np.clip(x_test_quantum, 0.0, np.pi)

    return PreparedFeatures(
        x_train_classical=x_train_classical,
        x_test_classical=x_test_classical,
        x_train_quantum=x_train_quantum,
        x_test_quantum=x_test_quantum,
        y_train=y_train,
        y_test=y_test,
        selected_features=selected_features,
    )


def split_signal_returns(test: pd.DataFrame) -> np.ndarray:
    return test["excess_return_5d"].to_numpy(dtype=float)

