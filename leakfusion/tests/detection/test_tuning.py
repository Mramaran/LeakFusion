"""Tests for tune_cusum_thresholds — empirical h selection per residual."""
import numpy as np
import pytest

from leakfusion.src.detection.tuning import tune_cusum_thresholds


def test_clean_normal_stream_picks_low_h():
    """Pure N(0,1) noise: tuner picks small h (textbook range 5-7).

    Note: textbook ARL₀ tables (Page 1954) assume rising-edge counting; our
    two-sided CUSUM with 30% hysteresis deadband fires for ~3 samples per
    false-alarm crossing, amplifying per-sample FAR ~3x. Empirically on N(0,1)
    seed 42, h=5 → FAR≈1.15%, h=6 → FAR≈0.48%, so the smallest h meeting the
    1% target is h=6. Bound h<=7 distinguishes clean noise from heavy tails
    (next test, t-distribution, requires h>=8).
    """
    rng = np.random.default_rng(42)
    z = rng.normal(0.0, 1.0, size=20000)
    config = tune_cusum_thresholds({"R1": z}, target_far=0.01)
    assert "R1" in config
    assert config["R1"]["k"] == 0.5
    assert config["R1"]["h"] <= 7.0
    assert config["R1"]["FAR_measured"] <= 0.01


def test_heavy_tailed_stream_requires_higher_h():
    """A heavy-tailed (t-distribution) z-stream needs h > 5 to hit FAR <= 1%."""
    rng = np.random.default_rng(7)
    # Student-t with df=3 has heavy tails; scale to roughly N(0,1)-ish
    z = rng.standard_t(df=3, size=20000) * 0.7
    config = tune_cusum_thresholds({"R6": z}, target_far=0.01)
    assert config["R6"]["h"] >= 5.0
    assert config["R6"]["FAR_measured"] <= 0.01


def test_multi_residual_returns_per_residual_h():
    """Each residual gets independently tuned h."""
    rng = np.random.default_rng(1)
    streams = {
        "R1": rng.normal(0.0, 1.0, size=10000),
        "R2": rng.normal(0.0, 1.0, size=10000),
    }
    config = tune_cusum_thresholds(streams, target_far=0.01)
    assert set(config.keys()) == {"R1", "R2"}
    for r in ("R1", "R2"):
        assert "k" in config[r] and "h" in config[r] and "FAR_measured" in config[r]


def test_nan_samples_excluded_from_tuning():
    """NaN samples in the stream are excluded from the FAR denominator."""
    rng = np.random.default_rng(3)
    z = rng.normal(0.0, 1.0, size=10000)
    z_with_nan = np.copy(z)
    z_with_nan[::5] = np.nan  # 20% NaN
    config = tune_cusum_thresholds({"R3": z_with_nan}, target_far=0.01)
    # Should still pick a valid h (not crash on NaN)
    assert config["R3"]["h"] > 0
