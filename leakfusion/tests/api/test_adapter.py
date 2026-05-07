import pandas as pd

from leakfusion.api.adapter import residuals_and_events_to_readings


def _fake_residuals(n: int) -> pd.DataFrame:
    return pd.DataFrame([{
        "row_index": i,
        "R1": 0.0, "R2": 0.0, "R3": 0.0, "R4": 0.0, "R5": 0.0, "R6": 0.0,
        "z_R1": 0.1, "z_R2": 0.1, "z_R3": 0.1, "z_R4": 0.1, "z_R5": 0.1, "z_R6": 0.1,
        "rpm_bin": 1400, "load_bin": 0.5,
        "op_point_extrapolated": False,
        "leak_zone": "no_leak", "leak_severity": 0.0,
    } for i in range(n)])


def _fake_source(n: int, rpm: int = 1400, load: float = 0.5) -> pd.DataFrame:
    return pd.DataFrame({"engine_rpm": [rpm] * n, "load_fraction": [load] * n})


def test_healthy_run_no_alerts():
    readings = residuals_and_events_to_readings(
        _fake_residuals(60), [], _fake_source(60)
    )
    assert len(readings) == 60
    assert all(not r.alert_triggered for r in readings)
    assert all(r.detected_zone is None for r in readings)
    assert all(r.severity == 0 for r in readings)
    for r in readings:
        assert r.zone_probabilities.zone1 == 0.2
        assert r.zone_probabilities.zone3a == 0.2


def test_leak_event_passes_backend_zone_through():
    res = _fake_residuals(100)
    src = _fake_source(100)
    event = {
        "event_id": "e1",
        "timestamp_idx": 40,
        "end_idx": 60,
        "tier": "CRITICAL",
        "predicted_zone": "zone3a",
        "predicted_zone_proba": 0.92,
        "predicted_severity": 0.05,
        "signature_status": "matched",
    }
    readings = residuals_and_events_to_readings(res, [event], src)
    assert all(not readings[i].alert_triggered for i in range(40))
    assert all(readings[i].alert_triggered for i in range(40, 61))
    assert readings[45].detected_zone == "zone3a"
    assert readings[45].zone_probabilities.zone3a >= 0.9
    assert readings[45].severity == 3   # round(0.05 * 50)
    assert readings[45].event_tier == "CRITICAL"


def test_adapter_returns_zscores_not_raw_residuals():
    """The UI labels the per-frame residual values with a 'σ' suffix and uses
    z-score thresholds (|x|>=3 = CRITICAL). The adapter MUST therefore expose
    z-scores from the residuals_df ('z_R1'..'z_R6'), not the raw physical-unit
    residuals ('R1'..'R6'). Raw R6 (Kelvin) of +78 would always show CRITICAL.
    """
    res = pd.DataFrame([{
        "row_index": 0,
        "R1": 999.0, "R2": 999.0, "R3": 999.0,
        "R4": 999.0, "R5": 999.0, "R6": 999.0,
        "z_R1": 0.1, "z_R2": 0.2, "z_R3": -0.1,
        "z_R4": 0.3, "z_R5": -0.2, "z_R6": 0.15,
        "rpm_bin": 1400, "load_bin": 0.5,
        "op_point_extrapolated": False,
        "leak_zone": "no_leak", "leak_severity": 0.0,
    }])
    src = _fake_source(1)
    [reading] = residuals_and_events_to_readings(res, [], src)
    # All residuals should reflect the small z-scores, NOT the huge raw values.
    assert abs(reading.residuals.r1) < 1.0, f"got r1={reading.residuals.r1}"
    assert abs(reading.residuals.r6) < 1.0, f"got r6={reading.residuals.r6}"
    assert reading.residuals.r1 == 0.1
    assert reading.residuals.r6 == 0.15


def test_warn_tier_event_is_yellow_warning_not_leak():
    """WARN-tier events surface as 'EARLY WARNING' (event_tier='WARN') in the
    React UI: the candidate zone is shown and zone probabilities reflect the
    ML's pick, but alert_triggered stays False so the 3D viewer does NOT pulse
    and the HDBSCAN escalation popup does NOT fire (Streamlit's WARN banner
    doesn't escalate either). This mirrors the reference status semantics.
    """
    res = _fake_residuals(100)
    src = _fake_source(100)
    event = {
        "event_id": "w1",
        "timestamp_idx": 30,
        "end_idx": 60,
        "tier": "WARN",
        "predicted_zone": "zone2",
        "predicted_zone_proba": 1.0,
        "predicted_severity": 0.02,
        "signature_status": "novel",
    }
    readings = residuals_and_events_to_readings(res, [event], src)
    in_window = readings[40]
    assert in_window.alert_triggered is False, "WARN must not trip the leak alert"
    assert in_window.event_tier == "WARN"
    assert in_window.detected_zone == "zone2", "WARN should surface candidate zone"
    assert in_window.severity == 0, "WARN events have severity 0 (no confirmation)"
    assert in_window.hdbscan_status == "Known Pattern", (
        "WARN must not trigger the HDBSCAN escalation popup"
    )
    assert in_window.zone_probabilities.zone2 == 1.0
    # Frames outside the WARN window stay fully healthy.
    assert readings[10].event_tier is None
    assert readings[10].alert_triggered is False


def test_novel_signature_flags_unknown():
    res = _fake_residuals(100)
    src = _fake_source(100)
    event = {
        "event_id": "e2", "timestamp_idx": 50, "end_idx": 60, "tier": "CRITICAL",
        "predicted_zone": None, "predicted_zone_proba": None, "predicted_severity": None,
        "signature_status": "novel",
    }
    readings = residuals_and_events_to_readings(res, [event], src)
    assert readings[55].alert_triggered
    assert readings[55].detected_zone is None
    assert readings[55].hdbscan_status == "Unknown — flag for review"
