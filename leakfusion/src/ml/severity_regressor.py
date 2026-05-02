"""Stage 3 severity regressor — XGBoost (squared loss) + residual sigma."""
from __future__ import annotations
import numpy as np
from sklearn.model_selection import GridSearchCV, GroupKFold
from xgboost import XGBRegressor


def train_severity(X, y, groups, *, seed: int = 42) -> tuple[XGBRegressor, float]:
    """Train XGBRegressor with 5x5 grid search; return (model, residual_sigma).

    residual_sigma is std of training-fold prediction residuals — used downstream
    to build a 95% CI as pred +/- 1.96 * sigma.
    """
    base = XGBRegressor(
        objective="reg:squarederror",
        random_state=seed,
        tree_method="hist",
        n_jobs=-1,
    )
    param_grid = {
        "n_estimators": [200, 500],
        "max_depth": [4, 6, 8],
        "learning_rate": [0.05, 0.1],
    }
    cv = GroupKFold(n_splits=5)
    gs = GridSearchCV(base, param_grid, scoring="neg_mean_absolute_error", cv=cv, n_jobs=-1)
    gs.fit(X, y, groups=groups)

    best = gs.best_estimator_
    pred = best.predict(X)
    sigma = float(np.std(y - pred, ddof=1))
    return best, sigma
