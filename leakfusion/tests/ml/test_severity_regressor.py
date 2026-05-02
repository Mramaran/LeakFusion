"""Stage 3 severity regressor — XGBoost + residual sigma for CI."""
import numpy as np
import pytest


@pytest.fixture
def synthetic_severity_data():
    """Severity ~ linear in z_R1..z_R6; sev in [0, 0.15] in 5 levels."""
    rng = np.random.default_rng(0)
    n_groups = 50
    rows_per_group = 30
    levels = np.array([0.01, 0.05, 0.075, 0.10, 0.15])

    X_list, y_list, g_list = [], [], []
    for gid in range(n_groups):
        sev = rng.choice(levels)
        signal = sev * 20.0  # |z| roughly proportional to severity
        for _ in range(rows_per_group):
            row = rng.standard_normal(15) * 0.3
            row[0] = -signal + rng.standard_normal() * 0.5  # z_R1 negative for leak
            row[1] = -signal + rng.standard_normal() * 0.5  # z_R2 negative for leak
            X_list.append(row)
            y_list.append(sev)
            g_list.append(gid)
    return np.array(X_list), np.array(y_list), np.array(g_list)


def test_train_severity_returns_regressor_and_sigma(synthetic_severity_data):
    from leakfusion.src.ml.severity_regressor import train_severity

    X, y, groups = synthetic_severity_data
    reg, sigma = train_severity(X, y, groups, seed=42)
    assert hasattr(reg, "predict")
    assert sigma > 0
    assert np.isfinite(sigma)


def test_train_severity_mae_below_target(synthetic_severity_data):
    from leakfusion.src.ml.severity_regressor import train_severity

    X, y, groups = synthetic_severity_data
    Xt, yt, gt = X[:-300], y[:-300], groups[:-300]
    Xv, yv = X[-300:], y[-300:]

    reg, _ = train_severity(Xt, yt, gt, seed=42)
    pred = reg.predict(Xv)
    mae = np.abs(pred - yv).mean()
    assert mae < 0.025, f"Expected MAE < 0.025, got {mae:.4f}"


def test_train_severity_sigma_in_reasonable_range(synthetic_severity_data):
    from leakfusion.src.ml.severity_regressor import train_severity

    X, y, groups = synthetic_severity_data
    _, sigma = train_severity(X, y, groups, seed=42)
    # sigma should be at least the discretization step (~0.025) and well under target range
    assert 0.001 < sigma < 0.05, f"Sigma {sigma:.4f} out of expected range"
