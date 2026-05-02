"""Stage 3 predictor — ZoneSeverityPredictor with uncertainty fallback."""
import numpy as np
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_calibrated_clf():
    clf = MagicMock()
    clf.classes_ = np.array(["zone1", "zone2", "zone3a", "zone3b", "zone4"])
    clf.predict_proba = MagicMock(return_value=np.array([[0.7, 0.1, 0.1, 0.05, 0.05]]))
    return clf


@pytest.fixture
def mock_severity_reg():
    reg = MagicMock()
    reg.predict = MagicMock(return_value=np.array([0.08]))
    return reg


def _row():
    return {
        "engine_rpm": 1400.0, "load_fraction": 0.5, "maf": 80.0, "fuel_flow": 5.0,
        "torque": 900.0, "boost_pressure": 180.0, "intake_manifold_pressure": 175.0,
        "t_boost": 320.0, "t_intake": 305.0, "t_intake_manifold": 310.0,
        "t_exhaust_manifold": 750.0, "t_turbine_outlet": 680.0,
        "t_aftertreatment_inlet": 650.0, "exhaust_manifold_pressure": 220.0,
        "exhaust_backpressure": 115.0, "ambient_pressure": 101.3,
        "ambient_temperature": 298.0, "turbo_speed": 85000.0, "lambda_sensor": 1.4,
    }


def test_predict_returns_decision_when_high_confidence(mock_calibrated_clf, mock_severity_reg):
    from leakfusion.src.ml.predict import ZoneSeverityPredictor

    predictor = ZoneSeverityPredictor(
        zone_clf=mock_calibrated_clf,
        severity_reg=mock_severity_reg,
        severity_sigma=0.01,
        feature_columns=["z_R1"] * 15,  # Only count matters for stub
    )
    feats = np.zeros((1, 15))
    out = predictor.predict_from_features(feats, op_point_extrapolated=False)
    assert out["ml_status"] == "ml_decision"
    assert out["predicted_zone"] == "zone1"
    assert out["predicted_zone_proba"] == pytest.approx(0.7)
    assert 0 <= out["predicted_severity"] <= 0.15
    assert len(out["predicted_severity_ci"]) == 2


def test_predict_returns_uncertain_when_extrapolated(mock_calibrated_clf, mock_severity_reg):
    from leakfusion.src.ml.predict import ZoneSeverityPredictor
    predictor = ZoneSeverityPredictor(
        zone_clf=mock_calibrated_clf, severity_reg=mock_severity_reg,
        severity_sigma=0.01, feature_columns=["z_R1"] * 15,
    )
    feats = np.zeros((1, 15))
    out = predictor.predict_from_features(feats, op_point_extrapolated=True)
    assert out["ml_status"] == "ml_uncertain"
    assert out["predicted_zone"] == "uncertain"


def test_predict_returns_uncertain_when_low_proba(mock_severity_reg):
    from leakfusion.src.ml.predict import ZoneSeverityPredictor
    clf = MagicMock()
    clf.classes_ = np.array(["zone1", "zone2", "zone3a", "zone3b", "zone4"])
    clf.predict_proba = MagicMock(return_value=np.array([[0.3, 0.2, 0.2, 0.15, 0.15]]))

    predictor = ZoneSeverityPredictor(
        zone_clf=clf, severity_reg=mock_severity_reg,
        severity_sigma=0.01, feature_columns=["z_R1"] * 15,
    )
    feats = np.zeros((1, 15))
    out = predictor.predict_from_features(feats, op_point_extrapolated=False)
    assert out["ml_status"] == "ml_uncertain"


def test_predict_clips_severity_to_valid_range(mock_calibrated_clf):
    from leakfusion.src.ml.predict import ZoneSeverityPredictor
    reg = MagicMock()
    reg.predict = MagicMock(return_value=np.array([0.50]))  # Out of range

    predictor = ZoneSeverityPredictor(
        zone_clf=mock_calibrated_clf, severity_reg=reg,
        severity_sigma=0.01, feature_columns=["z_R1"] * 15,
    )
    feats = np.zeros((1, 15))
    out = predictor.predict_from_features(feats, op_point_extrapolated=False)
    assert out["predicted_severity"] == pytest.approx(0.15)
    assert out["predicted_severity_clipped"] is True
