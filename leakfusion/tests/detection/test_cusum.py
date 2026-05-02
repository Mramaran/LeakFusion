"""Tests for CusumChannel — two-sided Page 1954 CUSUM with hysteresis."""
import math

import pytest

from leakfusion.src.detection.cusum import CusumChannel


def test_constant_zero_never_fires():
    ch = CusumChannel(name="R1", k=0.5, h=5.0)
    for _ in range(1000):
        assert ch.update(0.0) is False


def test_persistent_high_z_fires_within_expected_samples():
    """At z=3sigma persistent, with k=0.5 and h=5, should fire within ~3 samples
    (c_pos accumulates 2.5 per step, crosses 5 on step 3)."""
    ch = CusumChannel(name="R1", k=0.5, h=5.0)
    fired_at = None
    for i in range(20):
        if ch.update(3.0):
            fired_at = i
            break
    assert fired_at is not None
    assert fired_at <= 3, f"Expected fire by sample 3, fired at {fired_at}"


def test_persistent_low_z_fires_two_sided():
    """Negative drift fires via c_neg accumulator."""
    ch = CusumChannel(name="R1", k=0.5, h=5.0)
    fired_at = None
    for i in range(20):
        if ch.update(-3.0):
            fired_at = i
            break
    assert fired_at is not None
    assert fired_at <= 3


def test_nan_sample_does_not_fire_and_preserves_state():
    """NaN samples return False without mutating state (Isermann §7.2.1)."""
    ch = CusumChannel(name="R3", k=0.5, h=5.0)
    # accumulate to just below h
    for _ in range(2):
        ch.update(2.0)
    c_pos_before = ch.state.c_pos
    c_neg_before = ch.state.c_neg
    # NaN sample
    assert ch.update(float("nan")) is False
    assert ch.update(None) is False
    assert ch.state.c_pos == c_pos_before
    assert ch.state.c_neg == c_neg_before


def test_hysteresis_keeps_fired_above_exit_threshold():
    """Once fired, channel stays fired while CUSUM > 0.7 * h, even if z drops."""
    ch = CusumChannel(name="R1", k=0.5, h=5.0)
    # Push CUSUM above h
    for _ in range(5):
        ch.update(3.0)
    assert ch.update(3.0) is True
    # Now feed neutral z=0.5 — c_pos stops growing but doesn't reset
    # At this point c_pos should still be > 0.7 * 5.0 = 3.5
    fired = ch.update(0.5)
    assert fired is True, "Hysteresis should keep channel fired above 0.7*h"


def test_hysteresis_clears_when_below_exit_threshold():
    """Once CUSUM drops below 0.7 * h, channel reports not fired."""
    ch = CusumChannel(name="R1", k=0.5, h=5.0)
    for _ in range(5):
        ch.update(3.0)
    assert ch.update(3.0) is True
    # Drain c_pos with z=0 (drops 0.5/step via -k); avoid negative z which
    # would grow c_neg via the two-sided update and re-fire the channel.
    for _ in range(30):
        ch.update(0.0)
    # Both accumulators should be near 0 now
    assert ch.update(0.0) is False


def test_state_resets_under_zero_input():
    """c_pos = max(0, c_pos + z - k); under z < k it monotonically drains."""
    ch = CusumChannel(name="R1", k=0.5, h=5.0)
    ch.update(3.0)  # c_pos = 2.5
    ch.update(0.0)  # c_pos = max(0, 2.5 + 0 - 0.5) = 2.0
    assert ch.state.c_pos == pytest.approx(2.0)
    for _ in range(10):
        ch.update(0.0)
    assert ch.state.c_pos == 0.0
    assert ch.state.c_neg == 0.0
