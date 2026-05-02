"""Stage 3 zone classifier — calibrated RF."""
import numpy as np
import pytest


@pytest.fixture
def synthetic_zone_data():
    """5 zones x 40 groups x 20 rows = 4000 rows. Each zone has a distinguishable mean."""
    rng = np.random.default_rng(42)
    n_groups_per_zone = 40
    rows_per_group = 20
    zones = ["zone1", "zone2", "zone3a", "zone3b", "zone4"]

    X_list, y_list, g_list = [], [], []
    gid = 0
    zone_centers = {
        "zone1":  np.array([-2.5, -2.5, 0.0, 0.0, 0.0, 0.0] + [0]*9),
        "zone2":  np.array([0.0, 0.0, 0.0, 0.0, 0.0, 2.5] + [0]*9),
        "zone3a": np.array([-1.5, -1.5, -2.0, 0.0, 0.0, 0.0] + [0]*9),
        "zone3b": np.array([0.0, 0.0, 0.0, -2.5, 0.0, 0.0] + [0]*9),
        "zone4":  np.array([-1.0, -1.0, 0.0, 0.0, -1.5, 0.0] + [0]*9),
    }
    for zone in zones:
        for _ in range(n_groups_per_zone):
            mean = zone_centers[zone]
            for _ in range(rows_per_group):
                X_list.append(mean + rng.standard_normal(15) * 0.3)
                y_list.append(zone)
                g_list.append(gid)
            gid += 1
    return np.array(X_list), np.array(y_list), np.array(g_list)


def test_train_zone_returns_calibrated_classifier(synthetic_zone_data):
    from leakfusion.src.ml.zone_classifier import train_zone
    from sklearn.calibration import CalibratedClassifierCV

    X, y, groups = synthetic_zone_data
    clf = train_zone(X, y, groups, seed=42)
    assert isinstance(clf, CalibratedClassifierCV)


def test_train_zone_predicts_correctly_on_held_out_synthetic(synthetic_zone_data):
    from leakfusion.src.ml.zone_classifier import train_zone

    X, y, groups = synthetic_zone_data
    # Hold out last 200 rows.
    Xt, yt, gt = X[:-200], y[:-200], groups[:-200]
    Xv, yv = X[-200:], y[-200:]

    clf = train_zone(Xt, yt, gt, seed=42)
    pred = clf.predict(Xv)
    accuracy = (pred == yv).mean()
    assert accuracy > 0.7, f"Expected >0.7 accuracy, got {accuracy:.3f}"


def test_train_zone_predict_proba_sums_to_one(synthetic_zone_data):
    from leakfusion.src.ml.zone_classifier import train_zone

    X, y, groups = synthetic_zone_data
    clf = train_zone(X, y, groups, seed=42)
    proba = clf.predict_proba(X[:5])
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-6)
