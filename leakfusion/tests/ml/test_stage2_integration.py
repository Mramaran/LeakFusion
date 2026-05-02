"""Stage 2 + Stage 3 integration: AlertEvent gets augmented with ml_* fields."""
from unittest.mock import MagicMock
import numpy as np

from leakfusion.src.detection.cusum import CusumChannel
from leakfusion.src.detection.detector import LeakDetector


def _make_channels():
    return {f"R{i}": CusumChannel(name=f"R{i}", k=0.5, h=5.0) for i in range(1, 7)}


def _meta(extrapolated=False):
    return {"rpm_bin": 1400, "load_bin": 0.5, "op_point_extrapolated": extrapolated}


def test_alert_event_has_default_ml_skipped_when_no_predictor():
    """Without predictor, AlertEvent has ml_status='ml_skipped' and None ml fields."""
    detector = LeakDetector(
        channels=_make_channels(),
        persistence_samples=10,
        idle_holdoff_samples=5,
        cooldown_samples=10,
    )
    z = {"R1": -3.0, "R2": -3.0, "R3": 0.0, "R4": 0.0, "R5": 0.0, "R6": 0.0}
    event = None
    for _ in range(20):
        event = detector.update(z, _meta())
        if event is not None:
            break
    assert event is not None
    assert getattr(event, "ml_status", None) == "ml_skipped"
    assert event.predicted_zone is None


def test_alert_event_has_ml_fields_when_predictor_provided():
    """With predictor + row_features, AlertEvent fields are populated."""
    from leakfusion.src.ml.predict import ZoneSeverityPredictor

    clf = MagicMock()
    clf.classes_ = np.array(["zone1", "zone2", "zone3a", "zone3b", "zone4"])
    clf.predict_proba = MagicMock(return_value=np.array([[0.8, 0.05, 0.05, 0.05, 0.05]]))
    reg = MagicMock()
    reg.predict = MagicMock(return_value=np.array([0.07]))

    predictor = ZoneSeverityPredictor(
        zone_clf=clf, severity_reg=reg, severity_sigma=0.01,
        feature_columns=["z_R1"] * 15,
    )

    detector = LeakDetector(
        channels=_make_channels(),
        persistence_samples=10,
        idle_holdoff_samples=5,
        cooldown_samples=10,
        predictor=predictor,
    )

    feats = np.zeros((1, 15))
    z = {"R1": -3.0, "R2": -3.0, "R3": 0.0, "R4": 0.0, "R5": 0.0, "R6": 0.0}
    event = None
    for _ in range(20):
        event = detector.update(z, _meta(), row_features=feats, op_point_extrapolated=False)
        if event is not None:
            break

    assert event is not None
    assert getattr(event, "ml_status", None) == "ml_decision"
    assert event.predicted_zone == "zone1"
    assert event.predicted_zone_proba == 0.8


def test_alert_event_ml_uncertain_when_extrapolated():
    """With predictor but op_point extrapolated, ml_status = ml_uncertain."""
    from leakfusion.src.ml.predict import ZoneSeverityPredictor

    clf = MagicMock()
    clf.classes_ = np.array(["zone1", "zone2", "zone3a", "zone3b", "zone4"])
    clf.predict_proba = MagicMock(return_value=np.array([[0.8, 0.05, 0.05, 0.05, 0.05]]))
    reg = MagicMock()
    reg.predict = MagicMock(return_value=np.array([0.07]))

    predictor = ZoneSeverityPredictor(
        zone_clf=clf, severity_reg=reg, severity_sigma=0.01,
        feature_columns=["z_R1"] * 15,
    )

    detector = LeakDetector(
        channels=_make_channels(),
        persistence_samples=10,
        idle_holdoff_samples=5,
        cooldown_samples=10,
        predictor=predictor,
    )

    feats = np.zeros((1, 15))
    z = {"R1": -3.0, "R2": -3.0, "R3": 0.0, "R4": 0.0, "R5": 0.0, "R6": 0.0}
    event = None
    for _ in range(20):
        event = detector.update(z, _meta(), row_features=feats, op_point_extrapolated=True)
        if event is not None:
            break

    assert event is not None
    assert event.ml_status == "ml_uncertain"
    assert event.predicted_zone == "uncertain"
