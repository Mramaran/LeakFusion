"""Tests for enriched per-zone inspection recommendations."""
import pytest

from leakfusion.src.demo.recommendations import ZONE_ACTIONS, get_action


@pytest.mark.parametrize("zone", ["zone1", "zone2", "zone3a", "zone3b", "zone4"])
def test_every_zone_has_action(zone):
    action = ZONE_ACTIONS[zone]
    assert action["headline"], f"{zone} headline empty"
    assert len(action["bullets"]) >= 2, f"{zone} needs >=2 bullets"

def test_get_action_returns_default_for_no_leak():
    a = get_action("no_leak")
    assert a["headline"]
    assert "no action" in a["headline"].lower() or "monitoring" in a["headline"].lower()

def test_get_action_unknown_zone_safe():
    a = get_action("zone_does_not_exist")
    assert a["headline"]
    assert isinstance(a["bullets"], list)
