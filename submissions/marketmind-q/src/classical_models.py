"""Classical ML baselines for MarketMind-Q."""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

try:
    from xgboost import XGBClassifier

    XGBOOST_AVAILABLE = True
except Exception:  # pragma: no cover - depends on local optional dependency
    XGBClassifier = None
    XGBOOST_AVAILABLE = False


def build_classical_models(y_train: np.ndarray, *, random_state: int = 42) -> dict[str, object]:
    models: dict[str, object] = {
        "logistic_regression": LogisticRegression(class_weight="balanced", max_iter=2000, random_state=random_state),
        "rbf_svm": SVC(C=1.0, gamma="scale", class_weight="balanced", probability=True, random_state=random_state),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=5,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            random_state=random_state,
            n_jobs=-1,
        ),
    }
    if XGBOOST_AVAILABLE:
        positives = max(1, int(np.sum(y_train == 1)))
        negatives = max(1, int(np.sum(y_train == 0)))
        models["xgboost"] = XGBClassifier(
            n_estimators=250,
            max_depth=3,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            scale_pos_weight=negatives / positives,
            random_state=random_state,
            n_jobs=1,
        )
    return models

