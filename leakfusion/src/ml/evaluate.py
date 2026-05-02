"""Stage 3 evaluation — macro-F1, bootstrap CIs, ECE, MAE."""
from __future__ import annotations
import numpy as np
from sklearn.metrics import f1_score


def macro_f1(y_true, y_pred) -> float:
    return float(f1_score(y_true, y_pred, average="macro", zero_division=0))


def bootstrap_macro_f1_ci(
    y_true, y_pred, *, n_resamples: int = 200, seed: int = 42, alpha: float = 0.05
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    n = len(y_true)
    samples = []
    for _ in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        samples.append(macro_f1(y_true[idx], y_pred[idx]))
    samples = np.array(samples)
    lo = float(np.quantile(samples, alpha / 2))
    hi = float(np.quantile(samples, 1 - alpha / 2))
    return lo, hi


def expected_calibration_error(
    y_true, proba, classes, *, n_bins: int = 10
) -> float:
    """Standard ECE: |accuracy - confidence| weighted by bin size, summed.

    proba: (n_samples, n_classes), columns aligned with `classes`.
    """
    classes = np.asarray(classes)
    y_true = np.asarray(y_true)
    proba = np.asarray(proba)
    confidences = proba.max(axis=1)
    pred_class_idx = proba.argmax(axis=1)
    pred_classes = classes[pred_class_idx]
    correct = (pred_classes == y_true).astype(float)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        in_bin = (confidences >= lo) & (confidences < hi if i < n_bins - 1 else confidences <= hi)
        if not in_bin.any():
            continue
        acc_bin = correct[in_bin].mean()
        conf_bin = confidences[in_bin].mean()
        ece += (in_bin.sum() / n) * abs(acc_bin - conf_bin)
    return float(ece)


def mae(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true - y_pred)))


def bootstrap_mae_ci(
    y_true, y_pred, *, n_resamples: int = 200, seed: int = 42, alpha: float = 0.05
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    n = len(y_true)
    samples = []
    for _ in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        samples.append(mae(y_true[idx], y_pred[idx]))
    samples = np.array(samples)
    lo = float(np.quantile(samples, alpha / 2))
    hi = float(np.quantile(samples, 1 - alpha / 2))
    return lo, hi
