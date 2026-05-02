"""Tests for derived_fields.py — UI-facing computed strings."""
import pytest

from leakfusion.src.demo.derived_fields import severity_label


@pytest.mark.parametrize("sev,expected", [
    (0.00,  "Low (~0.0% flow loss)"),
    (0.04,  "Low (~4.0% flow loss)"),
    (0.05,  "Moderate (~5.0% flow loss)"),
    (0.075, "Moderate (~7.5% flow loss)"),
    (0.099, "Moderate (~9.9% flow loss)"),
    (0.10,  "High (~10.0% flow loss)"),
    (0.15,  "High (~15.0% flow loss)"),
])
def test_severity_label_buckets(sev, expected):
    assert severity_label(sev) == expected


from leakfusion.src.demo.derived_fields import decision


@pytest.mark.parametrize("event,expected", [
    ({"tier": "CRITICAL", "predicted_severity": 0.10},  "NO-GO"),
    ({"tier": "CRITICAL", "predicted_severity": 0.075}, "NO-GO"),  # boundary
    ({"tier": "CRITICAL", "predicted_severity": 0.074}, "GO"),
    ({"tier": "CRITICAL", "predicted_severity": 0.0},   "GO"),
    ({"tier": "CRITICAL"},                              "GO"),  # missing severity
    ({"tier": "WARN",     "predicted_severity": 0.20},  "GO"),  # WARN never NO-GO
])
def test_decision(event, expected):
    assert decision(event) == expected


from leakfusion.src.demo.derived_fields import confidence_pct, ZONE_DISPLAY


def test_confidence_pct_basic():
    assert confidence_pct(0.967) == "96.7%"
    assert confidence_pct(1.0)   == "100.0%"
    assert confidence_pct(0.0)   == "0.0%"

def test_confidence_pct_none():
    assert confidence_pct(None) == "n/a"

def test_zone_display_covers_all_zones():
    expected_keys = {"zone1", "zone2", "zone3a", "zone3b", "zone4", "no_leak"}
    assert set(ZONE_DISPLAY.keys()) >= expected_keys

def test_zone_display_zone3a_matches_screenshot():
    assert ZONE_DISPLAY["zone3a"] == "Zone 3a — Exhaust Pre-Aftertreatment"


from leakfusion.src.demo.derived_fields import residual_status_badge


def test_status_normal_below_2sigma():
    badge = residual_status_badge("R1", z=0.5, fired_residuals=set(), primary="R3")
    assert badge == ("NORMAL", "green")

def test_status_high_primary():
    badge = residual_status_badge("R3", z=4.8, fired_residuals={"R3", "R4"}, primary="R3")
    assert badge == ("HIGH-PRIMARY", "red")

def test_status_high_confirming_when_not_primary():
    badge = residual_status_badge("R4", z=3.2, fired_residuals={"R3", "R4"}, primary="R3")
    assert badge == ("HIGH-CONFIRMING", "red")

def test_status_low_supporting_when_outside_signature():
    badge = residual_status_badge("R6", z=-2.1, fired_residuals={"R3"}, primary="R3")
    assert badge == ("LOW-SUPPORTING", "orange")

def test_status_uses_absolute_z():
    badge = residual_status_badge("R6", z=-4.5, fired_residuals={"R3", "R6"}, primary="R6")
    assert badge == ("HIGH-PRIMARY", "red")
