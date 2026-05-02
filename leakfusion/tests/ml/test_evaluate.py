"""Stage 3 evaluation — macro-F1 + bootstrap CI + ECE + MAE."""
import numpy as np
import pytest


def test_macro_f1_perfect_prediction_is_one():
    from leakfusion.src.ml.evaluate import macro_f1
    y = np.array(["zone1", "zone2", "zone3a", "zone3b", "zone4"] * 10)
    assert macro_f1(y, y) == pytest.approx(1.0)


def test_macro_f1_random_baseline_below_0_5():
    from leakfusion.src.ml.evaluate import macro_f1
    rng = np.random.default_rng(0)
    zones = np.array(["zone1", "zone2", "zone3a", "zone3b", "zone4"])
    y_true = rng.choice(zones, size=500)
    y_pred = rng.choice(zones, size=500)
    assert macro_f1(y_true, y_pred) < 0.5


def test_bootstrap_macro_f1_ci_brackets_point_estimate():
    from leakfusion.src.ml.evaluate import macro_f1, bootstrap_macro_f1_ci
    rng = np.random.default_rng(1)
    zones = np.array(["zone1", "zone2", "zone3a", "zone3b", "zone4"])
    y_true = rng.choice(zones, size=400)
    y_pred = y_true.copy()
    flip = rng.choice(len(y_true), size=40, replace=False)
    y_pred[flip] = rng.choice(zones, size=40)

    point = macro_f1(y_true, y_pred)
    lo, hi = bootstrap_macro_f1_ci(y_true, y_pred, n_resamples=200, seed=42)
    assert 0.0 <= lo <= point <= hi <= 1.0
    assert hi - lo > 0  # nonzero width


def test_bootstrap_returns_finite_values():
    from leakfusion.src.ml.evaluate import bootstrap_macro_f1_ci
    y = np.array(["zone1"] * 100 + ["zone2"] * 100)
    pred = y.copy()
    lo, hi = bootstrap_macro_f1_ci(y, pred, n_resamples=200, seed=42)
    assert np.isfinite(lo) and np.isfinite(hi)


def test_ece_is_zero_for_perfect_calibration():
    """When proba == one-hot (1.0 for true class, 0.0 elsewhere), ECE is 0."""
    from leakfusion.src.ml.evaluate import expected_calibration_error
    classes = ["zone1", "zone2", "zone3a", "zone3b", "zone4"]
    y_true = np.array(["zone1", "zone2", "zone3a"])
    proba = np.array([
        [1.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0, 0.0],
    ])
    ece = expected_calibration_error(y_true, proba, classes)
    assert ece == pytest.approx(0.0, abs=1e-6)


def test_ece_is_in_unit_interval():
    from leakfusion.src.ml.evaluate import expected_calibration_error
    classes = ["zone1", "zone2"]
    rng = np.random.default_rng(3)
    n = 200
    y_true = rng.choice(classes, size=n)
    proba = rng.dirichlet([1, 1], size=n)
    ece = expected_calibration_error(y_true, proba, classes, n_bins=10)
    assert 0.0 <= ece <= 1.0


def test_mae_is_zero_for_perfect_prediction():
    from leakfusion.src.ml.evaluate import mae
    y = np.array([0.05, 0.10, 0.15])
    assert mae(y, y) == pytest.approx(0.0)


def test_mae_returns_absolute_mean():
    from leakfusion.src.ml.evaluate import mae
    y_true = np.array([0.10, 0.10])
    y_pred = np.array([0.08, 0.12])
    assert mae(y_true, y_pred) == pytest.approx(0.02)


def test_bootstrap_mae_ci_shape():
    from leakfusion.src.ml.evaluate import bootstrap_mae_ci
    rng = np.random.default_rng(2)
    y_true = rng.uniform(0, 0.15, size=200)
    y_pred = y_true + rng.normal(0, 0.01, size=200)
    lo, hi = bootstrap_mae_ci(y_true, y_pred, n_resamples=200, seed=42)
    assert lo <= hi
    assert lo >= 0
