"""Tests for SignatureMatcher — §10.4 zone signature lookup."""
from leakfusion.src.detection.signatures import (
    ZONE_SIGNATURES, match_signature,
)


def test_empty_fired_set_returns_no_candidates():
    assert match_signature(frozenset()) == set()


def test_r6_alone_matches_zone2():
    """Zone 2's signature is {R6}; any superset including R6 should match zone2."""
    assert "zone2" in match_signature(frozenset({"R6"}))


def test_r4_alone_matches_zone3b():
    assert "zone3b" in match_signature(frozenset({"R4"}))


def test_r1_r2_matches_zone1_zone3a_zone4():
    """The {R1, R2} signature is shared by zone1, zone3a, zone4 (all boost-drop)."""
    candidates = match_signature(frozenset({"R1", "R2"}))
    assert candidates == {"zone1", "zone3a", "zone4"}


def test_compound_fired_set_matches_all_subset_signatures():
    """{R1, R2, R6} fired -> zone1, zone3a, zone4 (via {R1,R2}) + zone2 (via {R6})."""
    candidates = match_signature(frozenset({"R1", "R2", "R6"}))
    assert candidates == {"zone1", "zone2", "zone3a", "zone4"}


def test_unknown_residual_returns_empty_set():
    """Fired set with only unknown residuals -> no zone matches."""
    assert match_signature(frozenset({"R7"})) == set()


def test_r1_alone_does_not_match_zone1():
    """zone1's signature is {R1, R2} — R1 alone is insufficient."""
    assert match_signature(frozenset({"R1"})) == set()


def test_signatures_table_canonical_keys():
    """Stage 1 contract: exactly 5 zones; zone2 alone is {R6}; zone3b alone is {R4}."""
    assert set(ZONE_SIGNATURES.keys()) == {"zone1", "zone2", "zone3a", "zone3b", "zone4"}
    assert ZONE_SIGNATURES["zone2"] == frozenset({"R6"})
    assert ZONE_SIGNATURES["zone3b"] == frozenset({"R4"})
    assert ZONE_SIGNATURES["zone1"] == ZONE_SIGNATURES["zone3a"] == ZONE_SIGNATURES["zone4"]
