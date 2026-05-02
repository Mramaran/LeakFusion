"""Stage 3 features: build_feature_frame + helpers."""
import pandas as pd
import pytest


def test_op_cell_id_is_deterministic_for_same_bins():
    from leakfusion.src.ml.features import op_cell_id
    a = op_cell_id(rpm_bin=1200, load_bin=0.5)
    b = op_cell_id(rpm_bin=1200, load_bin=0.5)
    assert a == b


def test_op_cell_id_differs_across_cells():
    from leakfusion.src.ml.features import op_cell_id
    assert op_cell_id(1200, 0.5) != op_cell_id(1400, 0.5)
    assert op_cell_id(1200, 0.5) != op_cell_id(1200, 0.75)


def test_op_cell_id_is_int():
    from leakfusion.src.ml.features import op_cell_id
    assert isinstance(op_cell_id(1200, 0.5), int)


def test_safe_ratio_handles_zero_denominator():
    from leakfusion.src.ml.features import safe_ratio
    assert safe_ratio(10.0, 0.0) == pytest.approx(10.0 / 1e-6)
    assert safe_ratio(0.0, 0.0) == 0.0


def test_safe_ratio_normal_division():
    from leakfusion.src.ml.features import safe_ratio
    assert safe_ratio(10.0, 2.0) == pytest.approx(5.0)


def test_safe_ratio_handles_negative_denom():
    from leakfusion.src.ml.features import safe_ratio
    # Use abs floor — ratio sign should follow numerator/denom.
    assert safe_ratio(10.0, -2.0) == pytest.approx(-5.0)


def test_thermal_gradient_is_signed_difference():
    from leakfusion.src.ml.features import thermal_gradient
    assert thermal_gradient(t_exh_manifold=750.0, t_ats_inlet=650.0) == pytest.approx(100.0)
    assert thermal_gradient(t_exh_manifold=600.0, t_ats_inlet=700.0) == pytest.approx(-100.0)


def test_lambda_deviation_subtracts_baseline():
    from leakfusion.src.ml.features import lambda_deviation
    assert lambda_deviation(1.4) == pytest.approx(0.0)
    assert lambda_deviation(1.6) == pytest.approx(0.2)
    assert lambda_deviation(1.2) == pytest.approx(-0.2)


import numpy as np


@pytest.fixture
def small_leak_frame():
    """Tiny synthetic leak_labeled-shaped frame with 2 zones x 2 severities x 5 rows."""
    rows = []
    for zone in ["zone1", "zone2"]:
        for severity in [0.05, 0.10]:
            for i in range(5):
                rows.append({
                    "engine_rpm": 1400.0,
                    "load_fraction": 0.50,
                    "maf": 80.0,
                    "fuel_flow": 5.0,
                    "torque": 900.0,
                    "boost_pressure": 180.0,
                    "intake_manifold_pressure": 175.0,
                    "t_boost": 320.0,
                    "t_intake": 305.0,
                    "t_intake_manifold": 310.0,
                    "t_exhaust_manifold": 750.0,
                    "t_turbine_outlet": 680.0,
                    "t_aftertreatment_inlet": 650.0,
                    "exhaust_manifold_pressure": 220.0,
                    "exhaust_backpressure": 115.0,
                    "ambient_pressure": 101.3,
                    "ambient_temperature": 298.0,
                    "turbo_speed": 85000.0,
                    "lambda_sensor": 1.4,
                    "leak_zone": zone,
                    "leak_severity": severity,
                    "timestamp": float(i),
                })
    return pd.DataFrame(rows)


def test_build_feature_frame_returns_X_y_zone_y_sev_groups(small_leak_frame, tmp_path):
    """build_feature_frame((df, calibration_path)) returns 4 arrays of equal length."""
    from leakfusion.src.ml.features import build_feature_frame

    cal_path = "leakfusion/models/calibration.json"
    X, y_zone, y_sev, groups = build_feature_frame(small_leak_frame, cal_path)

    assert len(X) == len(y_zone) == len(y_sev) == len(groups)
    assert X.shape[1] == 15, f"Expected 15 features, got {X.shape[1]}"


def test_build_feature_frame_drops_no_leak_rows(small_leak_frame):
    from leakfusion.src.ml.features import build_feature_frame, FEATURE_COLUMNS

    df = small_leak_frame.copy()
    df.loc[0, "leak_zone"] = "no_leak"
    df.loc[0, "leak_severity"] = 0.0

    X, y_zone, y_sev, groups = build_feature_frame(df, "leakfusion/models/calibration.json")
    assert len(X) == len(small_leak_frame) - 1
    assert "no_leak" not in y_zone


def test_build_feature_frame_columns_match_schema(small_leak_frame):
    from leakfusion.src.ml.features import build_feature_frame, FEATURE_COLUMNS
    X, _, _, _ = build_feature_frame(small_leak_frame, "leakfusion/models/calibration.json")
    assert list(X.columns) == FEATURE_COLUMNS
    assert len(FEATURE_COLUMNS) == 15


def test_build_feature_frame_groups_collapse_same_run(small_leak_frame):
    """Rows from same (zone, sev, rpm_bin, load_bin) get same group id."""
    from leakfusion.src.ml.features import build_feature_frame
    _, _, _, groups = build_feature_frame(small_leak_frame, "leakfusion/models/calibration.json")
    # 2 zones x 2 severities at fixed (rpm, load) = 4 unique groups
    assert len(set(groups)) == 4


def test_build_feature_row_returns_15_element_vector():
    """build_feature_row produces a 15-element vector aligned with FEATURE_COLUMNS."""
    from leakfusion.src.ml.features import build_feature_row, FEATURE_COLUMNS

    residual_row = pd.Series({
        "z_R1": -2.0, "z_R2": -1.5, "z_R3": 0.0, "z_R4": 0.0, "z_R5": 0.0, "z_R6": 0.0,
        "R1": -10.0, "R2": -50.0, "R3": 0.0, "R4": 0.0, "R5": 0.0, "R6": 0.0,
        "rpm_bin": 1400, "load_bin": 0.5, "op_point_extrapolated": False,
    })
    sensor_row = pd.Series({
        "engine_rpm": 1400.0, "load_fraction": 0.5, "boost_pressure": 180.0,
        "exhaust_manifold_pressure": 220.0, "exhaust_backpressure": 115.0,
        "t_exhaust_manifold": 750.0, "t_aftertreatment_inlet": 650.0,
        "lambda_sensor": 1.4, "maf": 80.0,
    })
    feats = build_feature_row(residual_row, sensor_row)
    assert feats.shape == (15,)
    assert len(FEATURE_COLUMNS) == 15
