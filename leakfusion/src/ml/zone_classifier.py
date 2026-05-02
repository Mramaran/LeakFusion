"""Stage 3 zone classifier — RF with isotonic probability calibration."""
from __future__ import annotations
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold


def train_zone(X, y, groups, *, seed: int = 42) -> CalibratedClassifierCV:
    """Train RF with 5x5 grid search + isotonic calibration.

    Returns a fitted CalibratedClassifierCV ready for predict_proba.
    """
    base = RandomForestClassifier(class_weight="balanced", random_state=seed, n_jobs=-1)
    param_grid = {
        "n_estimators": [200, 400],
        "max_depth": [6, 10, None],
        "min_samples_leaf": [1, 5],
    }
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    gs = GridSearchCV(base, param_grid, scoring="f1_macro", cv=cv, n_jobs=-1)
    gs.fit(X, y, groups=groups)

    calibrated = CalibratedClassifierCV(gs.best_estimator_, method="isotonic", cv=3)
    calibrated.fit(X, y)
    return calibrated
