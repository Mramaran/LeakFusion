"""Load fraction estimator: derive load_fraction from (rpm, fuel_flow) using syn-engine's combustion model."""
import pandas as pd
import pytest
from leakfusion.src.load_estimator import estimate_load_fraction, add_load_fraction_column


def test_zero_fuel_flow_returns_zero_load():
    assert estimate_load_fraction(rpm=1200, fuel_flow=0.0) == pytest.approx(0.0, abs=0.01)


def test_high_fuel_flow_caps_at_one():
    assert estimate_load_fraction(rpm=1200, fuel_flow=10.0) == pytest.approx(1.0, abs=0.01)


def test_intermediate_fuel_flow_gives_intermediate_load():
    load = estimate_load_fraction(rpm=1200, fuel_flow=2.0)
    assert 0.0 < load < 1.0


def test_higher_rpm_same_fuel_means_lower_load():
    # At higher RPM, the engine can accept more fuel, so same fuel = lower relative load
    load_1200 = estimate_load_fraction(rpm=1200, fuel_flow=2.0)
    load_1600 = estimate_load_fraction(rpm=1600, fuel_flow=2.0)
    assert load_1600 < load_1200


def test_add_load_fraction_column():
    df = pd.DataFrame({
        "engine_rpm": [1000, 1200, 1400, 1600],
        "fuel_flow": [1.5, 2.5, 3.0, 3.5],
    })
    out = add_load_fraction_column(df)
    assert "load_fraction" in out.columns
    assert (out["load_fraction"] >= 0.0).all()
    assert (out["load_fraction"] <= 1.0).all()
