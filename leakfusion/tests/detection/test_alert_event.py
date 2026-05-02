"""Tests for AlertEvent dataclass + ZONE_RECOMMENDATIONS lookup."""
from leakfusion.src.detection.detector import (
    AlertEvent, Tier, ZONE_RECOMMENDATIONS, recommendation_for,
)


def test_tier_enum_values():
    assert Tier.WARN.value == "WARN"
    assert Tier.CRITICAL.value == "CRITICAL"


def test_alert_event_fields():
    ev = AlertEvent(
        event_id="abc",
        timestamp_idx=42,
        timestamp_s=4.2,
        tier=Tier.WARN,
        fired_residuals=["R1", "R2"],
        candidate_zones=["zone1", "zone3a", "zone4"],
        signature_status="matched",
        confidence="medium",
        time_above_threshold_s={"R1": 1.2, "R2": 0.6},
        explanation="R1, R2 elevated 1.2s — pattern matches zone1/3a/4",
        recommendation="(see recommendation_for)",
        op_point={"rpm_bin": 1400, "load_bin": 0.5, "op_point_extrapolated": False},
    )
    assert ev.tier is Tier.WARN
    assert ev.candidate_zones == ["zone1", "zone3a", "zone4"]
    assert ev.signature_status == "matched"


def test_recommendations_table_has_all_zones():
    assert set(ZONE_RECOMMENDATIONS.keys()) == {"zone1", "zone2", "zone3a", "zone3b", "zone4"}


def test_recommendation_for_single_zone():
    rec = recommendation_for({"zone1"}, signature_status="matched")
    assert rec == ZONE_RECOMMENDATIONS["zone1"]


def test_recommendation_for_multi_zone_joins_with_or():
    rec = recommendation_for({"zone1", "zone3a", "zone4"}, signature_status="matched")
    # Order may vary; assert all three texts appear in the OR-joined result
    for zone in ("zone1", "zone3a", "zone4"):
        assert ZONE_RECOMMENDATIONS[zone].split(" ")[1] in rec or ZONE_RECOMMENDATIONS[zone][:20] in rec
    assert " OR " in rec


def test_recommendation_for_novel_signature():
    rec = recommendation_for(set(), signature_status="novel")
    assert "novelty" in rec.lower() or "stage 4" in rec.lower()
