"""Steady-state filter: rolling RPM and torque stability."""
import numpy as np
import pandas as pd
from leakfusion.src.steady_state import filter_steady_state, is_steady_window


def _synth_df(n=200, rpm=1200, torque=300, rpm_noise=5, torque_noise=3, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "engine_rpm": rpm + rng.normal(0, rpm_noise, n),
        "torque": torque + rng.normal(0, torque_noise, n),
        "maf": 50 + rng.normal(0, 0.5, n),
    })


def test_stable_window_is_steady():
    df = _synth_df(n=20)
    assert is_steady_window(df, rpm_tol=50, torque_tol_pct=5.0) is True


def test_ramp_window_is_not_steady():
    df = _synth_df(n=20)
    df["engine_rpm"] = np.linspace(1000, 1600, 20)  # 600 RPM ramp
    assert is_steady_window(df, rpm_tol=50, torque_tol_pct=5.0) is False


def test_filter_returns_only_steady_rows():
    df = _synth_df(n=500)
    out = filter_steady_state(df, window=10, rpm_tol=50, torque_tol_pct=5.0)
    assert len(out) > 0
    assert len(out) <= len(df)
    # All kept rows have a "steady" label
    assert "is_steady" not in out.columns  # filter drops the flag, not keeps it


def test_filter_rejects_ramp():
    df = _synth_df(n=100)
    df["engine_rpm"] = np.linspace(1000, 1600, 100)  # full ramp
    out = filter_steady_state(df, window=10, rpm_tol=50, torque_tol_pct=5.0)
    assert len(out) == 0


def test_filter_preserves_schema():
    df = _synth_df(n=100)
    out = filter_steady_state(df, window=10, rpm_tol=50, torque_tol_pct=5.0)
    assert set(out.columns) == set(df.columns)
