"""Tests for dashboard_components - payload-builder logic only."""
from leakfusion.ui.dashboard_components import build_status_banner_payload


def test_banner_no_events_is_all_clear():
    p = build_status_banner_payload([])
    assert p["variant"] == "all_clear"
    assert "ALL CLEAR" in p["headline"]
    assert p["color"] == "green"

def test_banner_warn_only():
    events = [{"tier": "WARN", "candidate_zones": ["zone1", "zone4"]}]
    p = build_status_banner_payload(events)
    assert p["variant"] == "warn_only"
    assert "EARLY WARNING" in p["headline"]
    assert p["color"] == "yellow"

def test_banner_critical_picks_latest():
    events = [
        {"tier": "WARN", "timestamp_s": 3.0, "candidate_zones": ["zone1"]},
        {"tier": "CRITICAL", "timestamp_s": 5.0, "predicted_zone": "zone3a",
         "predicted_zone_proba": 0.967, "predicted_severity": 0.042},
        {"tier": "CRITICAL", "timestamp_s": 8.5, "predicted_zone": "zone3a",
         "predicted_zone_proba": 0.971, "predicted_severity": 0.048},
    ]
    p = build_status_banner_payload(events)
    assert p["variant"] == "leak_confirmed"
    assert "LEAK CONFIRMED" in p["headline"]
    assert p["color"] == "red"
    assert p["zone_label"] == "Zone 3a — Exhaust Pre-Aftertreatment"
    assert p["confidence"] == "97.1%"  # latest CRITICAL
    # 0.048 < 0.05 -> Low bucket
    assert "Low" in p["severity_label"]
    assert p["decision"] in ("GO", "NO-GO")


import pandas as pd

from leakfusion.ui.dashboard_components import build_residual_bars_payload


def test_residual_bars_payload_six_rows():
    residuals_df = pd.DataFrame({
        "z_R1": [0.2] * 60, "z_R2": [0.5] * 60,
        "z_R3": [4.8] * 60, "z_R4": [3.2] * 60,
        "z_R5": [0.8] * 60, "z_R6": [-2.1] * 60,
    })
    event = {
        "fired_residuals": ["R3", "R4"],
        "candidate_zones": ["zone3a"],
        "timestamp_s": 5.0,
    }
    rows = build_residual_bars_payload(residuals_df, event)
    assert len(rows) == 6
    by_name = {r["name"]: r for r in rows}
    assert by_name["R3"]["badge"] == "HIGH-PRIMARY"
    assert by_name["R3"]["color"] == "red"
    assert by_name["R4"]["badge"] in ("HIGH-PRIMARY", "LOW-CONFIRMING", "HIGH-CONFIRMING")
    assert by_name["R1"]["badge"] == "NORMAL"
    # peak |z| sign preserved in z_value
    assert by_name["R6"]["z_value"] == -2.1


from leakfusion.ui.dashboard_components import build_recommendation_payload


def test_recommendation_for_critical_zone3a():
    event = {"tier": "CRITICAL", "predicted_zone": "zone3a"}
    p = build_recommendation_payload(event)
    assert "manifold" in p["headline"].lower()
    assert len(p["bullets"]) >= 2

def test_recommendation_for_warn_uses_first_candidate():
    event = {"tier": "WARN", "candidate_zones": ["zone1", "zone4"]}
    p = build_recommendation_payload(event)
    assert p["headline"]  # non-empty

def test_recommendation_no_event_is_no_action():
    p = build_recommendation_payload(None)
    assert "no action" in p["headline"].lower() or "monitoring" in p["headline"].lower()


from leakfusion.ui.dashboard_components import build_timeline_payload


def test_timeline_empty_events():
    p = build_timeline_payload([], duration_s=60.0)
    assert p["markers"] == []
    assert p["duration_s"] == 60.0
    assert p["default_index"] is None

def test_timeline_picks_latest_critical_as_default():
    events = [
        {"tier": "WARN", "timestamp_s": 1.0, "predicted_zone": None},
        {"tier": "CRITICAL", "timestamp_s": 4.0, "predicted_zone": "zone1"},
        {"tier": "CRITICAL", "timestamp_s": 8.0, "predicted_zone": "zone3a"},
    ]
    p = build_timeline_payload(events, duration_s=60.0)
    assert len(p["markers"]) == 3
    assert p["default_index"] == 2  # latest CRITICAL
