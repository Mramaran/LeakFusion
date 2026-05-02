"""Deterministic synthetic fill-in for columns NavicEngine lacks (turbo_speed, t_aftertreatment_inlet)."""
import pandas as pd
import pytest
from leakfusion.src.syn_fill import fill_missing_columns, deterministic_seed


def test_deterministic_seed_stable():
    assert deterministic_seed(1200, 0.75) == deterministic_seed(1200, 0.75)


def test_deterministic_seed_varies_with_input():
    assert deterministic_seed(1200, 0.75) != deterministic_seed(1200, 0.50)
    assert deterministic_seed(1200, 0.75) != deterministic_seed(1400, 0.75)


def test_fill_adds_missing_columns():
    df = pd.DataFrame({
        "engine_rpm": [1000, 1200, 1400, 1600],
        "torque": [200, 300, 290, 280],
        "fuel_flow": [1.7, 2.7, 3.2, 3.6],
        "load_fraction": [0.68, 0.90, 0.91, 0.90],
    })
    out = fill_missing_columns(df)
    assert "turbo_speed" in out.columns
    assert "t_aftertreatment_inlet" in out.columns
    assert len(out) == len(df)


def test_fill_is_deterministic_for_same_op_point():
    df = pd.DataFrame({
        "engine_rpm": [1200, 1200, 1200],
        "torque": [300, 300, 300],
        "fuel_flow": [2.7, 2.7, 2.7],
        "load_fraction": [0.90, 0.90, 0.90],
    })
    out1 = fill_missing_columns(df)
    out2 = fill_missing_columns(df)
    pd.testing.assert_series_equal(out1["turbo_speed"], out2["turbo_speed"])


def test_fill_values_are_physical():
    df = pd.DataFrame({
        "engine_rpm": [1200],
        "torque": [300],
        "fuel_flow": [2.7],
        "load_fraction": [0.90],
    })
    out = fill_missing_columns(df)
    ts = out["turbo_speed"].iloc[0]
    t_ats = out["t_aftertreatment_inlet"].iloc[0]
    assert 10_000 < ts < 200_000, f"turbo_speed {ts} outside physical range"
    assert 350 < t_ats < 900, f"t_aftertreatment_inlet {t_ats} outside physical range (K)"
