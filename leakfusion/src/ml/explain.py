"""Stage 3 explainability — permutation importance + SHAP TreeExplainer summary."""
from __future__ import annotations
import numpy as np
from sklearn.inspection import permutation_importance


def permutation_importance_dict(model, X, y, *, feature_names, n_repeats: int = 10, seed: int = 42) -> dict:
    """Sklearn permutation_importance -> {feature_name: mean_importance}."""
    result = permutation_importance(model, X, y, n_repeats=n_repeats, random_state=seed, n_jobs=-1)
    return {name: float(imp) for name, imp in zip(feature_names, result.importances_mean)}


def shap_summary(model, X_samples, *, feature_names) -> dict:
    """SHAP TreeExplainer values for a small sample of predictions.

    Returns a JSON-serializable summary; one entry per row of X_samples with
    per-feature contribution.
    """
    import shap

    # Unwrap CalibratedClassifierCV to get the underlying fit tree ensemble for TreeExplainer.
    if hasattr(model, "calibrated_classifiers_"):
        base = model.calibrated_classifiers_[0].estimator
    else:
        base = model

    explainer = shap.TreeExplainer(base)
    raw = explainer.shap_values(X_samples)
    # For multiclass, shap returns a list of arrays (one per class) OR a 3D array.
    if isinstance(raw, list):
        # Average |SHAP| across classes per (row, feature) for a class-agnostic summary.
        stacked = np.stack([np.abs(a) for a in raw], axis=-1)
        per_pred = stacked.mean(axis=-1)
    elif raw.ndim == 3:
        per_pred = np.abs(raw).mean(axis=-1)
    else:
        per_pred = np.abs(raw)

    predictions = []
    for i in range(X_samples.shape[0]):
        contributions = {name: float(per_pred[i, j]) for j, name in enumerate(feature_names)}
        predictions.append({"row_index": int(i), "feature_contributions": contributions})
    return {"predictions": predictions}
